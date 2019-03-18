# Python 3

# To start: navigate to the folder containing this file in your terminal and run: python3 main.py

import pandas as pd
import numpy as np
import geopandas as gpd

from shapely.geometry import Point, shape
from shapely.ops import linemerge
from pathlib import Path

import glob, os
import csv
import random 

# Set Folder Paths for shapefiles
# Folder containing missions
base_path = Path(__file__).parent
mission_folder = (base_path / "../work_sample/Missions/").resolve()
# Folder containing landing zone
lz_folder = (base_path / "../work_sample/Landing_Zone/LZ_points_WGS.shp").resolve()

# Import multiple shapefiles
def importShapeFiles(folder_directory):
    files = []
    os.chdir(folder_directory)
    for layers in glob.glob("*.shp"):
        layer = gpd.read_file(layers)
        files.append(layer)
    return files

# Import all missions
missionFiles = importShapeFiles(mission_folder)

# Import landing zones
lzFiles = gpd.read_file(lz_folder)

# Remove non-valid features from shapefile and add to Geopandas DataFrame, Add desired spatial projection if not already set
def validateAndBuffLZ(shapeFile, projection, buffSize):
    validate = []
    for index, row in shapeFile.iterrows():
        geometry = row['geometry']
        if geometry == None:
            continue
        else:
            validate.append(row)
    df = gpd.GeoDataFrame(validate)
    # Set projection
    df.crs = {'init' :'epsg:4326'}
    df.to_crs(epsg=projection)
    # Add Buffer to LZ
    df['geometry'] = df.geometry.buffer(buffSize / 100000)
    return df

# Validate shapefile missions and set projection to WGS 84, buffer by ~20 m 0.0002
LZ = validateAndBuffLZ(lzFiles, 4326, 20)

# User feedback
print('{}{}{}'.format("A total of ", len(missionFiles), " missions have been loaded..."))
print('{}{}{}'.format("A total of ", len(LZ), " LZ areas have been loaded..."))

# Dissolve and buffer function, inputs: imported missions, attribute field to dissolve by, buffer size (km)
def dissolveBuff(missions, dissolveBy, buffSize):
    # Add missions to Geopandas DataFrame
    mission_df = gpd.GeoDataFrame( pd.concat( missions, ignore_index=True))
    # Dissolve and Buffer missions by 3 meter
    dissolved = mission_df.dissolve(by=dissolveBy, aggfunc='first', as_index=False)
    output = dissolved['geometry'] = dissolved.geometry.buffer(buffSize / 100000)
    return output

# Buff and dissolve missions by 3 m 0.000003
flights = dissolveBuff(missionFiles, "Missn_Name", 3)

# Identify flights that enter the LZ area
def dangerZone(missions, landingZone):
    airspaceConflict = []
    for i in range(len(missions)):
        overlap = missions.geometry.iloc[i].intersects(landingZone.geometry.iloc[0])
        if overlap == True:
            airspaceConflict.append(str(i + 1))
    return airspaceConflict

dangerFlights = dangerZone(flights, LZ)

# Find all flights that do not enter no fly zone, requires output from dangerZone function
def removeDangerousFlights(dangerFlights):
    sorties = []
    for i in range(len(flights)):
        sorties.append(str(i + 1))
    for flight in dangerFlights:
        if flight in sorties:
            sorties.remove(flight)
    return sorties

safeFlights = removeDangerousFlights(dangerFlights)

def findSafeFlights(flights, dangerFlights, safeFlights):
    conflicts = {}
    safeFlights = {}
    # Detect overlap between flight paths
    for i in range(len(flights)):
        overlap = []
        for j in range(len(flights)):
            detectOverlap = flights.geometry.iloc[i].intersects(flights.geometry.iloc[j])
            if detectOverlap == True:
                overlap.append(str(j + 1))
        conflicts['{}{}'.format("Sortie", str(i + 1))] = overlap
    # Remove flights that enter the No Fly Zone
    for key, value in conflicts.items():
        for x in dangerFlights:
            if x in value:
                value.remove(x)
    # sort flights by least number of conflicts          
    output = sorted(conflicts.items(), key=lambda k: len(k[1]))
    return output

rankedFlightsbyConflicts = findSafeFlights(flights, dangerFlights, safeFlights)

# Drone flight manager:
# Input takes lists from rankedFlights, safeFlights, and dangerFlights as well as desired number of drones to be flown during mission sorties
# Finds optimal flight arrangements by taking the least number of conflicts and sorts them so that each flight appears once
# All flights are included with flights that enter the No Fly Zone placed towards the end of the mission sorties
def flightCommander(flights, safeFlights, dangerFlights, drones):
    sorties = {}
    flight_list = []
    # Append each flight starting with flights that have the least amount of spatial conflicts with others
    for i in range(len(flights)):
        flight = flights[i][1]
        previous = 0
        for j in range(len(flight)):
            if flight[j] not in flight_list:
                previous = int(flight[j - 1])
                if int(flight[j]) - 1 != previous:
                    flight_list.append(flight[j])
    # Append any remaining missing flights that were left out
    for i in range(len(safeFlights)):
        if safeFlights[i] not in flight_list:
            flight_list.append(safeFlights[i])
    for i in range(len(dangerFlights)):
        if dangerFlights[i] not in flight_list:
            flight_list.append(dangerFlights[i])
    # Final conflict check, compare each element to its next, if it is sequential, we need to shuffle it
    for i in range(len(flight_list) -1):
        j = random.randint(0, i + 1)
        # If two flight paths adjoin each other (creating a hazard), shuffle to a new index position
        if int(flight_list[i]) + 1 == int(flight_list[i + 1]):
            # Shuffle Swap
            flight_list[i], flight_list[j] = flight_list[j], flight_list[i]
    # Convert to numpy array     
    missions = np.array(list(flight_list))
    # Divide missions based on total number of flights and desired number of drones to be flown simultanously
    flightNum = int(np.ceil((len(missions) / drones)))
    # Split numpy array by flightNum
    flightDivider = np.array_split(missions, flightNum)
    counter = 0
    for i in range(len(flightDivider)):
        counter = counter + 1
        sorties['flight ' + str(counter)] = flightDivider[i]
    
    return sorties

flightList = flightCommander(rankedFlightsbyConflicts, safeFlights, dangerFlights, 3)

print('{}''{}'.format('The following flight sorties have been organized: ',flightList))
print("Flight deck approved...")

# Output location for flight plan
base = Path(__file__).parent
output_flight_plan = (base / "../work_sample/Flight_Plan").resolve()

# Output results to csv...
def outputToCSV(sorties, filePath):
    print("Creating CSV flight plan...")
    flight_list = []

    for flight_sorties, flights in sorties.items():
        output = {}
        output['Sorties'] = flight_sorties
        counter = 0
        for j in range(len(flights)):
            try:
                output['{}{}'.format('Drone_', str(counter + 1))] = flights[j]
            except:
                output['{}{}'.format('Drone_', str(counter + 1))] = 'No Flight'
            counter += 1

        flight_list.append(output)

    output_flights = '../Flight_Plan/fly_missions.csv'
    
    def addFlightHeaders(headers):
        output = []
        output.append('Sorties')
        for h in headers:
            output.append(h)
        return output
    
    with open(output_flights, "w", newline = '') as file:
        fieldnames = addFlightHeaders(list(flight_list[0].keys())[1:])
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for k in range(len(flight_list)):
            writer.writerow(flight_list[k])
    print("Flight plan created in Flight_Plan folder...")
    
outputToCSV(flightList, output_flight_plan)

print("Program complete")

