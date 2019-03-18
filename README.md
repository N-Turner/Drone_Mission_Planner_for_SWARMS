This repo features a mission planning tool for multiple simultaneous drone flights (a.k.a. SWARM flights). It takes in shapefiles of possible drone flights and a landing/take-off shapefile. The program develops an optimized flight plan to reduce the risk of mid-air drone collisions when flying multiple drones. Use at your own risk.

# How to use
Example data is included.
1) Download or fork/clone this repo
2) Place desired drone flights into Missions folder
3) Place a landing zone point shapefile in Landing_Zone folder
4) Run main.py file using python3

# Pre-reqs:
Requires the following python libraries to be installed:
  1) Geopandas (http://geopandas.org/)
  2) Shapely (https://pypi.org/project/Shapely/)
  3) Pandas, Numpy

# Start Application
```
python3 main.py
```
Flight Plan outputs to a CSV in Flight_Plan folder
