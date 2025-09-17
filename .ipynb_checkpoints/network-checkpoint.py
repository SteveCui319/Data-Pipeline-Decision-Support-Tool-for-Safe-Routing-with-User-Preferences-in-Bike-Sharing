import xml.etree.ElementTree as ET
import pandas as pd
from tqdm import tqdm
import numpy as np
import osmnx as ox
import networkx as nx

file_path = '../london_bike_network.graphml'
G = nx.read_graphml(file_path)

node_types = {
    "street_count": int,
    "x": float,
    "y": float
}

edge_types = {
    'osmid': str, 
    'access': str, 
    'highway': str, 
    'maxspeed': str, 
    'name': str, 
    'oneway': str, 
    'reversed': str, 
    'length': float
}

for attr_name, dtype in tqdm(node_types.items()):
    attrs = nx.get_node_attributes(G, attr_name)
    attrs_converted = {node: dtype(value) for node, value in attrs.items()}
    nx.set_node_attributes(G, attrs_converted, name=attr_name)

for attr_name, dtype in tqdm(edge_types.items()):
    attrs = nx.get_edge_attributes(G, attr_name)
    attrs_converted = {edge: dtype(value) for edge, value in attrs.items()}
    nx.set_edge_attributes(G, attrs_converted, name=attr_name)
    
G = nx.relabel_nodes(G, {node[0] : int(node[0]) for node in G.nodes(data=True)})

bike_road_nodes_data = []
for node in tqdm(G.nodes(data=True)):
    bike_road_nodes_data.append([node[0], node[1]['x'], node[1]['y'], node[1]['street_count']])
bike_road_nodes_df = pd.DataFrame(data=bike_road_nodes_data, columns=["id", "x", "y", "street_count"])

with open("livecyclehireupdates.xml", "r") as f:
    xml_data = f.read()

root = ET.fromstring(xml_data)

station_list = []

for station in tqdm(root.findall('station')):
    station_data = {}
    for child in station:
        tag = child.tag
        value = child.text
        try:
            if tag in ['name', 'terminalName']:
                value = str(value)
            elif tag in ['id', 'nbBikes', 'nbStandardBikes', 'nbEBikes', 'nbEmptyDocks', 'nbDocks']:
                value = int(value)
            elif tag in ['lat', 'long']:
                value = float(value)
            elif tag in ['installed', 'locked', 'temporary']:
                value = True if value.lower() == "true" else False
            else:
                continue
            station_data[tag] = value
        except:
            print(tag, value)
        
    station_list.append(station_data)
station_df = pd.DataFrame(data=station_list)

def get_station_coord(station_name):
    station = station_df[station_df.name == station_name]
    if len(station) != 1:
        return None, None
    lat, lon = station.lat.values[0], station.long.values[0]
    return lat, lon

def get_k_nearest_road_nodes(lat, lon, k=3, line_k=20):
    topK = bike_road_nodes_df.iloc[np.argsort((bike_road_nodes_df.x - lon)**2 + (bike_road_nodes_df.y - lat)**2)[:line_k]].copy()
    topK["distance"] = [ox.distance.great_circle(lat, lon, topK.iloc[i].y, topK.iloc[i].x) for i in range(len(topK))]
    topK = topK.sort_values(by="distance").iloc[:k]
    return topK.values.tolist()

def process_route(G, route):
    return pd.DataFrame([G.get_edge_data(route[idx], route[idx+1])[0] for idx in range(len(route) - 1)])

def get_shortest_route(G, start_node_id, dest_node_id):
    route = ox.routing.shortest_path(G, int(start_node_id), int(dest_node_id), weight='length', cpus=1)
    route = process_route(G, route)
    return route

# def get_all_shortest_route(start_station_name, dest_station_name, station_df, G, k=3, line_k=20):
#     start_lat, start_lon  = get_station_coord(start_station_name, station_df)
#     dest_lat, dest_lon = get_station_coord(dest_station_name, station_df)
#     print(start_station_name, start_lat, start_lon)
#     print(dest_station_name, dest_lat, dest_lon)

def get_all_shortest_route(start_lat, start_lon, dest_lat, dest_lon, k=3, line_k=20):
    
    start_road_nodes = get_k_nearest_road_nodes(start_lat, start_lon, k=k, line_k=line_k)
    dest_road_nodes = get_k_nearest_road_nodes(dest_lat, dest_lon, k=k, line_k=line_k)

    routes_summary = []
    routes_detail = {}
    for start_node in start_road_nodes:
        for dest_node in dest_road_nodes:
            route_id = f"{int(start_node[0])}-{int(dest_node[0])}"
            route = get_shortest_route(G, start_node[0], dest_node[0])
            routes_detail[route_id] = route
            routes_summary.append([int(start_node[0]), int(dest_node[0]), 
                                   start_node[-1], dest_node[-1], route.length.sum(),
                                   start_node[-1] + dest_node[-1] + route.length.sum()])

    return pd.DataFrame(data=routes_summary, columns=["start_node", "dest_node", 
                                                      "dist_start", "dist_dest", 
                                                      "route_length", "total_length"]), routes_detail