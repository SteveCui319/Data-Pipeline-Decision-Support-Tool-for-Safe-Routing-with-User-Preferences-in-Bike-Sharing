from flask import Flask, request, jsonify
from flask_cors import CORS
from route_network import RouteNetwork
import osmnx as ox

# from network import get_all_shortest_route

app = Flask(__name__)
CORS(app)

route_network = RouteNetwork()


@app.route('/search', methods=['GET'])
def search_station():
    query = request.args.get('query')
    if not query:
        return jsonify([])
    
    station_df = route_network.station_df
    matches = station_df[station_df['name'].str.contains(query, case=False)]

    result = [
        {"name": row['name'], "lat": row['lat'], "lon": row['lon'], "bikes": row["bikes"]}
        for _, row in matches.iterrows()
    ]

    return jsonify(result)


@app.route('/route', methods=['GET'])
def get_route():
    start_name = request.args.get('start')
    end_name = request.args.get('end')
    distance_coeff = float(request.args.get('distance', '0.0'))
    safety_coeff = float(request.args.get('safety', '0.0'))
    comfort_coeff = float(request.args.get('comfort', '0.0'))
    total_coeff = distance_coeff + safety_coeff + comfort_coeff 
    if total_coeff == 0:
        distance_weight, safety_weight, comfort_weight = 1, 0, 0
    else:
        distance_weight = distance_coeff / total_coeff 
        safety_weight = safety_coeff / total_coeff 
        comfort_weight = comfort_coeff / total_coeff 

    if not start_name or not end_name:
        return jsonify({"error": "Missing compulsory arguments start or end."}), 400

    try:
        result = route_network.plan_cycle_route(
            start_name=start_name,
            end_name=end_name,
            distance_weight=distance_weight,
            safety_weight=safety_weight,
            comfort_weight=comfort_weight
        )

        # Check for error responses
        if isinstance(result, dict) and 'error' in result:
            return jsonify({"error": result['error']}), 400
            
        if result is None:
            return jsonify({"error": "The path cannot be planned out"}), 500
        
        def extract_coordinates(geom):
            """Extract all coordinate points from the geometric object"""
            if geom.geom_type == 'Point':
                return [(geom.x, geom.y)]
            elif geom.geom_type == 'LineString':
                return list(geom.coords)
            elif geom.geom_type == 'MultiLineString':
                coords = []
                for line in geom.geoms:
                    coords.extend(list(line.coords))
                return coords
            return []
        
        # Return multiple paths in safe mode
        if isinstance(result, list):  # multiple route situation
            routes = []
            metrics = []

            for route_info in result:
                node_path = route_info["route"]
                gdf = ox.routing.route_to_gdf(route_network.G, node_path)
                
                coordinates = []
                for geom in gdf.geometry:
                    for point in extract_coordinates(geom):
                        coordinates.append({"lat": float(point[1]), "lon": float(point[0])})
                
                routes.append(coordinates)
                metrics.append({
                    "route_length": route_info["total_length"],
                    "safety_score": route_info["safety_factor"],
                    "comfort_score": route_info["comfort_factor"],
                    "combined_score": route_info["combined_score"]
                })

            return jsonify({
                "routes": routes,
                "metrics": metrics
            })
        
        else:  # single route situation
            if "path_nodes" not in result:
                return jsonify({"error": "The format of the path data is incorrect"}), 500
                
            node_path = result["path_nodes"]
            gdf = ox.routing.route_to_gdf(route_network.G, node_path)
            
            coordinates = []
            for geom in gdf.geometry:
                for point in extract_coordinates(geom):
                    coordinates.append({"lat": float(point[1]), "lon": float(point[0])})
            
            return jsonify({
                "routes": [coordinates],
                "metrics": [{
                    "route_length": result.get("total_distance", 0),
                    "walking_distance": result.get("walking_distance", 0)
                }]
            })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
