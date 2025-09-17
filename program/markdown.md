attributes_extract.ipynb

- Extracts and analyzes attribute values from nodes and edges in the bicycle network for further modeling and visualization.

set_network_attr.ipynb

- Processes the London cycling network by converting node/edge attributes, filling in missing values, and integrating accident data into the network.

set_network_attr_v2.ipynb

- Builds on the integrated accident data to further assign safety and comfort scores to the cycling network edges, supporting multi-criteria route planning.

cyclist_accidents.ipynb

- Processes the cyclist accident dataset, including data cleaning and coordinate conversion, preparing it for network integration.

route_network.py

- Core backend module for the cycling route planner. Handles data loading, station management, and pathfinding with multi-factor scoring.

app.py

- Flask-based backend API providing route planning services:
  - /search: Fuzzy search for stations by name (returns name and coordinates).
  - /route: Generates bike routes based on start/end stations and user preferences (distance, safety, comfort), returns route geometry and metrics.

index.html

- Frontend interface built with Leaflet and TailwindCSS.
- Supports map display, station search, interactive route visualization, and real-time preference adjustment for multi-route comparison.




