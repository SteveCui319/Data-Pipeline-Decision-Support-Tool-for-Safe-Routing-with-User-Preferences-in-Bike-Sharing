import time
import requests
import pandas as pd
import numpy as np
import osmnx as ox
import xml.etree.ElementTree as ET


class RouteNetwork:

    def __init__(self):
        file_path = '../data/london_bike_network_safety_comfort_score.graphml'
        self.G = ox.load_graphml(file_path)

        # load station data 
        self.station_df = self.load_tfl_data()
        if self.station_df.empty:
            raise Exception("bicycle station data cannot be loaded")
        else:
            print(self.station_df.head())
            print(f"A total of {len(self.station_df)} sites were loaded")


    def load_tfl_data(self, url="https://tfl.gov.uk/tfl/syndication/feeds/cycle-hire/livecyclehireupdates.xml"):
        """
        Obtain the bike data from the TfL data site and return the DataFrame containing the site
        """
        try:
            # Obtain and parse the xml dataset
            response = requests.get(url)
            root = ET.fromstring(response.content)

            station_list = []
            for station in root.findall('station'):
                station_data = {'valid': True}
                try:
                    # Extract core fields
                    station_data.update({
                        'id': int(station.find('id').text),
                        'name': station.find('name').text.strip(),
                        'lat': float(station.find('lat').text),
                        'lon': float(station.find('long').text),
                        'bikes': int(station.find('nbBikes').text),
                        'standardBikes': int(station.find('nbStandardBikes').text),
                        'eBikes': int(station.find('nbEBikes').text),
                        'docks': int(station.find('nbEmptyDocks').text)
                    })

                    # Validity check (If there is at least one vehicle at the site, 
                    # it is considered available; otherwise, it is marked as invalid)
                    station_data['valid'] = (station_data['bikes'] >= 1) 

                except(AttributeError, ValueError, TypeError) as e:
                    print(f"Parsing site error: {str(e)}")
                    station_data['valid'] = False

                station_list.append(station_data)

            return pd.DataFrame(station_list)

        except requests.exceptions.RequestException as e:
            print(f"Network request failed: {str(e)}")
            return pd.DataFrame()

        except ET.ParseError as e:
            print(f"XML parsing failed: {str(e)}")
            return pd.DataFrame()


    def get_station_coord(self, station_name, station_df, is_start=True): # is_start = True, indicates the starting point
        """
        Obtain the corresponding geographical coordinates based on the incoming starting point and ending point
        """
        # Fuzzy matching query
        matches = station_df[station_df['name'].str.contains(station_name, case=False)]
        if len(matches) == 0:
            raise ValueError(f"No matching site was found: {station_name}")

        # Prioritize valid sites
        valid_matches = matches[matches['valid']]
        
        for _, row in valid_matches.iterrows():
            available_bikes = row['bikes']
            # available_docks = row['docks']

            if is_start and available_bikes > 0:
                return row['lat'], row['lon'], row['name']
            elif not is_start:
                return row['lat'], row['lon'], row['name']
                
        raise ValueError(f"No available stations found: {station_name}")


    def get_nearest_road_node(self, lat, lon):
        """
        Return (node ID, distance to the site)
        """
        try:
            node_id, distance = ox.distance.nearest_nodes(self.G, X=lon, Y=lat, return_dist=True)
            print(f"The nearest node ID: {node_id}, with a distance of {distance:.2f} meters")
            return node_id, distance

        except Exception as e:
            print(f"Failed to find the nearest node: {str(e)}")
            return None, float('inf')

    def evaluateRouteScores(self, route):
        """
        Evaluate  and return the cycling score and factors of the current path
        """
        edge_safety_scores = []
        edge_comfort_scores = []
        node_safety_scores = []
        node_comfort_scores = []

        street_counts = 0
        cycleway_lanes = 0
        total_edges = 0

        # Handle node score
        for node in route:
            node_data = self.G.nodes[node]
            if 'safety_score' in node_data:
                node_safety_scores.append(float(node_data['safety_score']))
            if 'comfort_score' in node_data:
                node_comfort_scores.append(float(node_data['comfort_score']))
            if 'street_count' in node_data:
                street_counts += int(node_data['street_count'])

        # Handle edge score
        for i in range(len(route) - 1):  # iterate every pair of consecutive nodes in each path
            start_node = route[i]
            end_node = route[i + 1]
            total_edges += 1

            # obtain edge data
            if self.G.has_edge(start_node, end_node, 0):
                edge_data = self.G.edges[(start_node, end_node, 0)]
                if 'safety_score' in edge_data:
                    edge_safety_scores.append(float(edge_data['safety_score']))
                if 'comfort_score' in edge_data:
                    edge_comfort_scores.append(float(edge_data['comfort_score']))
                if 'highway' in edge_data and edge_data['highway'] == 'cycleway':
                    cycleway_lanes += 1

        # calculate average score
        safety_score = 0
        comfort_score = 0
        
        # Security score weight: 40% for nodes, 60% for edges
        if node_safety_scores:
            safety_score += 0.4 * np.mean(node_safety_scores)
        if edge_safety_scores:
            safety_score += 0.6 * np.mean(edge_safety_scores)
        
        # Comfort score weight: 30% for nodes, 70% for edges
        if node_comfort_scores:
            comfort_score += 0.3 * np.mean(node_comfort_scores)
        if edge_comfort_scores:
            comfort_score += 0.7 * np.mean(edge_comfort_scores)

        # Calculate the coverage rate of bicycle lanes
        cycle_coverage = cycleway_lanes / total_edges if total_edges > 0 else 0
        
        return safety_score, comfort_score, street_counts, cycle_coverage

    def findKBestRoutes(self, start_node, end_node, k, safety_weight, comfort_weight, distance_weight):
        """
        Taking into account both distance and safety factors comprehensively, return k optimal routes
        """
        # if distance_weight is None:
        #     distance_weight = 1.0 - safety_weight - comfort_weight

        routes = list(ox.routing.k_shortest_paths(self.G, start_node, end_node, k, weight="length")) # Yen's algorithm, obtain k shortest paths
        
        route_details = []
        for route in routes:
            safety_factor, comfort_factor, street_counts, lanes_coverage = self.evaluateRouteScores(route)
            gdf = ox.routing.route_to_gdf(self.G, route, weight="length")
            total_length = gdf["length"].sum()

            acc_list = []
            for num in gdf['casualty_count']:
                acc_list.append(num)

            accidents_counts = 0
            for num in acc_list:
                accidents_counts += int(num) 

            # store route details
            route_details.append({
                "route": route,
                "safety_factor": safety_factor,
                "comfort_factor": comfort_factor,
                "total_length": total_length,
                "street_count": street_counts,
                "cycleway_coverage": lanes_coverage,
                "accidents_count": accidents_counts
            })

        if not route_details:
            return []
            
        # Use weight factor to identify best route considering combined effect of safety and distance 
        lengths = [detail['total_length'] for detail in route_details]
        safeties = [detail['safety_factor'] for detail in route_details]
        comforts = [detail['comfort_factor'] for detail in route_details]
        
        max_length = max(lengths)
        min_length = min(lengths)
        max_safety = max(safeties) if safeties else 1
        min_safety = min(safeties) if safeties else 0
        max_comfort = max(comforts) if comforts else 1
        min_comfort = min(comforts) if comforts else 0

        # Calculate the comprehensive score of each path
        for detail in route_details:
            
            norm_length_score = 1.0 - (detail["total_length"] - min_length) / (max_length - min_length) # Normalized distance score (the shorter the distance, the higher the score)
            norm_safety_score = (detail["safety_factor"] - min_safety) / (max_safety - min_safety)      # Normalized safety score
            norm_comfort_score = (detail["comfort_factor"] - min_comfort) / (max_comfort - min_comfort) # Normalized comfort score
            
            # Overall score 
            combined_score = (distance_weight * norm_length_score + 
                            safety_weight * norm_safety_score + 
                            comfort_weight * norm_comfort_score)
            
            detail["combined_score"] = combined_score
        
        # Sort in descending order of the comprehensive score
        sorted_routes = sorted(route_details, key=lambda x: x["combined_score"], reverse=True)
        return sorted_routes

    def plan_cycle_route(self, start_name, end_name, distance_weight, safety_weight, comfort_weight):
        start_time = time.time()

        if self.station_df is None or self.station_df.empty:
            raise ValueError("The bicycle station data is not loaded or is empty")

        try:
            # step 1: Obtain the coordinates of valid bicycle stations
            start_lat, start_lon, start_name = self.get_station_coord(start_name, self.station_df, is_start=True)
            end_lat, end_lon, end_name = self.get_station_coord(end_name, self.station_df, is_start=False)
            print(f"start_lat: {start_lat}, start_lon: {start_lon}, starting point: {start_name}")
            print(f"end_lat: {end_lat}, end_lon: {end_lon}, destinaton: {end_name}")
            print()

            # step 2: Find the nearest road network node
            start_node, start_dist = self.get_nearest_road_node(start_lat, start_lon)
            end_node, end_dist = self.get_nearest_road_node(end_lat, end_lon)
            print()

            # step 3: Calculate the route based on the cycling indicators
            consider_multi_obj = safety_weight > 0 or comfort_weight > 0 or distance_weight > 0
            if consider_multi_obj:
                print(f"The following is the route after considering safety")
                print(f"Distance weight：{distance_weight}， Safety weight：{safety_weight}, Comfort weight：{comfort_weight}")
                k_optimal_route = self.findKBestRoutes(
                    start_node, end_node, k=5, 
                    safety_weight=safety_weight,
                    comfort_weight=comfort_weight,
                    distance_weight=distance_weight
                )

                end_time = time.time()
                time_count = end_time - start_time 

                if not k_optimal_route:
                    raise ValueError("No availble path could be found\n")

                # Print all options
                print("\nFind multiple optional paths:")
                for i, option in enumerate(k_optimal_route):
                    print(f"{i+1}. Overall score: {option['combined_score']:.4f}, "
                        f"Length: {option['total_length']:.2f}m, "
                        f"Safety: {option['safety_factor']:.4f}, "
                        f"Comfort: {option['comfort_factor']:.4f}",
                        f"Intersection: {option['street_count']:.2f}, "
                        f"Lanes coverage: {option['cycleway_coverage']*100:.2f}%, "
                        f"Accidents: {option['accidents_count']}")
                print(f"Route planning run times：{time_count:.2f} sec")

                return k_optimal_route

            else:
                print(f"Only consider distance metric")
                route = ox.routing.shortest_path(self.G, 
                                                 start_node, 
                                                 end_node, 
                                                 weight='length',
                                                 cpus=1)  # Using the Dijkstra algorithm, return the list of nodes that make up the shortest path

                if not route:
                    raise ValueError("NO available paths have found")

                # Obtain all the edges on the path
                edge_lengths = [self.G[u][v][k]['length'] for u, v, k in zip(route[:-1], route[1:], [0] * len(route))]
                total_length = sum(edge_lengths)

                print(f"A list of nodes that make up the shortest path: {route}")
                print(f"All edges on the path: {edge_lengths}")
                print(f"Shortest path: {total_length}m")
                print()

                return {
                    'start_station': start_name,
                    'end_station': end_name,
                    'path_nodes': route,
                    'total_distance': total_length,
                    'walking_distance': start_dist + end_dist
                }

        except Exception as e:
            print(f"Path planning failure: {str(e)}")
            return {"error": str(e)}



# if __name__ == "__main__":
#     rn = RouteNetwork()
#     rn.plan_cycle_route('Liverpool street', "King's Cross", 
#                         consider_safety_score=True, 
#                         safety_weight = 0.4,
#                         comfort_weight = 0.3,
#                         distance_weight = 0.7)