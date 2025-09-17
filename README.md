Data Pipeline & Decision Support Tool for Safe Routing with User Preferences in Bike Sharing 

Briefly speaking, a major goal of your project is to develop a methodology and, if time permits, a tool 
for assessing the bikeability of a bike sharing network. 
Bikeability measures how easy, practical, and safe it is to navigate with a bike in a certain area. 
There are plenty of works assessing the bikeability of areas with “bikeability indices”, but the 
suggestion is that you develop a data-driven methodology based on mapping and navigation 
software tailored to bike sharing. 

For this purpose, you may focus on the Santander Cycles bike sharing network in London. 
Transport for London (TfL) provides the geographic coordinates of the stations in the London 
bike sharing network (  link  ). 

The bikeability of a route between two stations in an urban environment is affected by 
several factors such as (1) spatial distance, (2) duration, (3) safety (number of past accidents 
and/or casualties), (4) bike lane coverage (percentage of route with a bike lane independent or 
not from the motor-vehicle road network), (5) road quality (potholes, last maintenance time, etc), 
(6) average and/or max speed limit, (7) slope (average inclination of route segments), and (8) 
number of intersections. You may want to use these metrics for assessing the bikeability of a 
route. 

By using OpenStreetMap and the OSMnx Python package, you can compute routes between 
any pair of stations in a bike sharing network. For this purpose, you can define some metric, e.g. 
spatial distance, which calculates the shortest path with respect to this metric. OSMnx should 
provide an implementation of the Dijkstra algorithm for doing this. You could use other metrics, 
e.g., bike lane coverage or number of intersections, for computing other paths. In this way, you 
will be able to compute multiple paths between a pair of stations. 

You can store the outcome in a directed multigraph, where each node is a station of the London 
bike sharing network. A pair of nodes is connected with multiple arcs. Each arc would 
correspond to a different route that somebody could follow for going from one station to another. 
Each arc would be associated with multiple values like the metrics mentioned above for 
assessing the bikeability of the corresponding route. 
In your project report, you could explain how OpenStreetMap can be used to represent routes 
(e.g. as a set of geographic coordinates) and how somebody can compute the shortest path 
between two points according to some metric.
