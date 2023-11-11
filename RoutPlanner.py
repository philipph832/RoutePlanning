# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 11:11:03 2023

@author: 
"""

import gpxpy
import pandas as pd
from geopy.distance import geodesic
from shapely.geometry import Point, MultiPoint
from shapely.ops import nearest_points
import os

import overpy
import gpxpy.gpx
import gpxpy.gpx as g
from pandas import DataFrame
import folium
import webbrowser
import datetime
from folium.plugins import MeasureControl, MiniMap
import easygui
import random


from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.course_message import CourseMessage
from fit_tool.profile.messages.course_point_message import CoursePointMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.profile_type import FileType, Manufacturer, Sport, Event, EventType, CoursePoint


# %%import, overpass query and storage
# from gpx_converter import Converter

# open and read gpx_file

gpx_file = open(easygui.fileopenbox())  # chose file to open with a dialogue
gpx = gpxpy.parse(gpx_file, version='1.1')
water = g.GPX();
new = g.GPX();

# extract filename for storage at end of code
filename = gpx_file.name;
filename = os.path.basename(filename)
filename = filename.replace('.gpx', '');
 
# make some empty stuff to fill later
gpx_trace = []
gpx_spur = []
gpx_length = []
gpx_string = ""

# read the track and put points into a list [[a,b],[c,d],...]
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            gpx_trace.append([point.latitude, point.longitude])
            gpx_spur.append([point.latitude, point.longitude, point.elevation])


# parse list into a string - so overpy likes it
for i, j in gpx_trace:
    gpx_string += "," + str(i) + "," + str(j)


# some random stuff so overpy is happy
# options for interpeter url. Change if one server is too busy

api = overpy.Overpass(url="https://overpass-api.de/api/interpreter")
# api = overpy.Overpass(url="https://overpass.kumi.systems/api/interpreter")
result = overpy.Result()


# query overpy

rad = 75;  # set searchradius
to = 250;  # set time of timeout in s
coords = [];


results = api.query( #perform an overpass query for certain nodes - define what you need on your own
    f"""[timeout:{to}];node["amenity"="drinking_water"](around:{rad}{gpx_string}); out;""")
# join water with existing gpx-track, safe a separte gpx with WPs only, repeat for every type of water, assign spec. symbols
for j in results.nodes:
    # type = water because garmin connect does not recognise drinking_water when transferring to fit_file
    gpx.waypoints.append(g.GPXWaypoint(j.lat, j.lon, name=str(
        j.id), type="WATER", symbol=("flag, blue"))); #this adds the new WP to the entire gpx
    water.waypoints.append(g.GPXWaypoint(j.lat, j.lon, name=str(
        j.id), type="Drinking_Water", symbol=("flag, blue")));  # this is only the WPs
    lon = j.lon;
    lat = j.lat;
    name = j.id;
    kind = j.tags["amenity"];
    if kind == "drinking_water":
        clr = 'blue'
    coords.append((lat, lon, name, kind, clr));

fountain = api.query(
    f"""[timeout:{to}];node["amenity"="fountain"](around:{rad}{gpx_string}); out; """)
for j in fountain.nodes:
    # my old edge only knows a few symbols. Airport is just one of them and therefore chosen here insted of fountain
    gpx.waypoints.append(g.GPXWaypoint(j.lat, j.lon, name=str(
        j.id), type="AID_STATION", symbol=("airport"))); #this adds the new WP to the entire gpx
    water.waypoints.append(g.GPXWaypoint(j.lat, j.lon, name=str(
        j.id), type="aid_station", symbol=("flag, red")));  # only the WPS
    lon = j.lon;
    lat = j.lat;
    name = j.id;
    kind = j.tags["amenity"];
    if kind == "fountain":
        clr = 'red'
    coords.append((lat, lon, name, kind, clr));
results.expand(fountain)

#repeat the above steps for all kinds of overpass querries. Or be more clever than me and write a better code so that the querrying can be done in one step

# prepare data and print WPs in dataframes
cols = ['lat', 'lon']
columns = ['lat', 'lon', 'id', 'kind', 'clr']
gpxSpur = DataFrame(gpx_trace, columns=cols)
WPs = DataFrame(coords, columns=columns)

# repeat for including the elevation information
cols = ['lat', 'lon', 'ele']
gpx_spur = DataFrame(gpx_spur, columns=cols)

# %% safe the new track

save_path_file = filename+"-water.gpx"

# write gpx name and track name according to file name
gpx.name = filename;
track.name = filename;

with open(save_path_file, "w") as f:  # entire track with WPs
    f.write(gpx.to_xml())


# %% plot on map
latmin = (WPs.lat.min())
latmax = (WPs.lat.max())
lonmin = (WPs.lon.min())
lonmax = (WPs.lon.max())
lataverage = (WPs.lat.median())
lonaverage = (WPs.lon.median())

# Create a map using Stamen Terrain, centered on min (lat and lon)
m = folium.Map(location=[lataverage, lonaverage], png_enabled=True
               # tiles = 'Stamen Terrain'
               )

spur = folium.Map(location=[lataverage, lonaverage],
               # tiles = 'Stamen Terrain'
               )

# calculate the distance between each point in the trace and store in a list
distances = []
previous_point = None
for point in gpx_trace:
    if previous_point:
        distances.append(gpxpy.geo.haversine_distance(
            previous_point[0], previous_point[1], point[0], point[1]))
    previous_point = point

# calculate cumulative distance and plot markers at 5 km intervals
kmMarker = folium.FeatureGroup(name='10km markers').add_to(m)
cumulative_distance = 0
cumdist = 0
for i, distance in enumerate(distances):
    cumulative_distance += distance
    cumdist += distance
    if cumulative_distance >= 10000:
        marker_location = gpx_trace[i]
        kmMarker.add_child(folium.Marker(location=marker_location,
                           tooltip=f"{int(cumdist/1000)} km", icon=folium.Icon(color='lightgray')).add_to(m))
        cumulative_distance -= 10000

# Add markers for waypoints color by type of amenity
waypoints = folium.FeatureGroup(name='Waypoints').add_to(m)
for i in range(len(WPs)):
    waypoints.add_child(folium.Marker(
        location=[WPs.lat[i], WPs.lon[i]],  # coordinates for the marker
        tooltip=(WPs.kind[i], WPs.id[i]),  # pop-up label for the marker
        icon=folium.Icon(color=WPs.clr[i])
    ))

# add markers displaying other information along the path
course = folium.FeatureGroup(name='course as points').add_to(m)
for i in range(len(gpxSpur)):
    course.add_child(folium.CircleMarker(
        location=[gpxSpur.lat[i], gpxSpur.lon[i]],
        tooltip=(f"{int(gpx_spur.ele[i])} m", f"{int(cumdist/1000)} km"),
        radius=0.01,
        color='blue',
        overlay='true'
    ))

# plot line with entire route
folium.PolyLine(locations=gpxSpur, tooltip=filename).add_to(
    folium.FeatureGroup(name='course as line').add_to(m))
m.fit_bounds(m.get_bounds(), padding=(30, 30))

# include layer control
folium.LayerControl(position='topright', collapsed=False).add_to(m)

# Add a MeasureControl
MeasureControl(position='topleft', primary_length_unit='km').add_to(m)

# Add a MiniMap to provide an overview of the map
MiniMap().add_to(m)

# safe as html and open in browser in next step
m.save(filename+"_map.html")

# open an HTML file on my own (Windows) computer
url = filename+"_map.html"
webbrowser.open(url, new=0)

# %% re-take the gpx, because I don't know any better way :-)
# Create a DataFrame to store the data
gpx_spur = []
gpx_df = [];

# read the track and put points into a list [[a,b],[c,d],...]
for track in gpx.tracks:
    for segment in track.segments:
        for point in segment.points:
            gpx_spur.append([point.latitude, point.longitude, point.elevation])
            gpx_df.append([point.latitude, point.longitude,
                          point.elevation, point.name, point.name, point.symbol])

cols = ['latitude', 'longitude', 'elevation', 'name', 'type', 'symbol']

gpxSpurdf = pd.DataFrame(gpx_df, columns=cols)

# %%calculate the closest point of the track to the waypoints

distance = 0.0;
course_records = []  # track points

prev_coordinate = None
length = []
time=[]
tottime=0
ldelta=[]
for track_point in gpx.tracks[0].segments[0].points:
    current_coordinate = (track_point.latitude, track_point.longitude)

    # calculate distance from previous coordinate and accumulate distance
    if prev_coordinate:
        delta = geodesic(prev_coordinate, current_coordinate).meters
    else:
        delta = 0.0

    distance += delta
    ldelta.append(delta)
    length.append(distance)
    dtime=delta/8 #calculate the time based on a velocity of 8m/s = 28.8km/h
    tottime += dtime
    time.append(tottime)
    prev_coordinate = current_coordinate
gpxSpurdf.insert(loc=6, column='distance', value=length)
gpxSpurdf.insert(loc=7, column='time', value=time)
gpxSpurdf.insert(loc=8, column='delta', value=ldelta)


WPs = []
near = [];
xyz = []
# Iterate through waypoints that are not on the track and identify nearest points on the track
for i in gpx.waypoints:
    WPs = Point(i.latitude, i.longitude)
    destinations = MultiPoint(gpx_spur)
    nearest_geoms = nearest_points(WPs, destinations)
    near_idx0 = nearest_geoms[0]
    near_idx1 = nearest_geoms[1]
    x = near_idx1.x; #x-coordinate of nearest point on the track of a certain WP
    y = near_idx1.y; #y-coordinate of nearest point on the track of a certain WP
    xyz.append((str(i.name), x, y, i.type, i.symbol))
    
xyzdf = pd.DataFrame(
    xyz, columns=['name', 'latitude', 'longitude', 'type', 'symbol'])

a = [];
for i in range(len(xyzdf)):
    lat = xyzdf.latitude[i]
    lon = xyzdf.longitude[i]
    gpxlat = gpxSpurdf.latitude
    a.append((gpxSpurdf[(gpxSpurdf.latitude == lat) #find index of waypoints with corresponding points on the track 
             & (gpxSpurdf.longitude == lon)].index))
xyzdf.insert(loc=5, column='indy', value=a)

b = []
CoursePoints = [];
for i in range(len(xyzdf)):
    for ii in range(len(a[i])):  #add the new Course points in the right position on the track itself = on "gpxSPurdf" as a representation of the track (some WPs might be multiple coursepoints, depending on the geomety of the track)
        gpxSpurdf.loc[[xyzdf.indy[i][ii]], 'name'] = xyzdf.name[i]
        gpxSpurdf.loc[[xyzdf.indy[i][ii]], 'type'] = xyzdf.type[i]
        gpxSpurdf.loc[[xyzdf.indy[i][ii]], 'symbol'] = xyzdf.symbol[i]
             
        CoursePoints.append((
            gpxSpurdf.name[xyzdf.indy[i][ii]],
            gpxSpurdf.type[xyzdf.indy[i][ii]],
            gpxSpurdf.symbol[xyzdf.indy[i][ii]],
            gpxSpurdf.latitude[xyzdf.indy[i][ii]],
            gpxSpurdf.longitude[xyzdf.indy[i][ii]],
            gpxSpurdf.elevation[xyzdf.indy[i][ii]],
            gpxSpurdf.distance[xyzdf.indy[i][ii]]-100, #subtract 100m from the distance, so that on the GPS the warning is a little in advance. Couldn't find any other way to trigger the warning
            gpxSpurdf.time[xyzdf.indy[i][ii]],
            gpxSpurdf.delta[xyzdf.indy[i][ii]],
            ))
        
CoursePoints = pd.DataFrame(CoursePoints, columns=[ #create a dataframe just for the new CoursePoints
                            'name', 'type', 'symbol', 'latitude', 'longitude', 'elevation', 'distance', 'time', 'delta'])
CoursePoints=CoursePoints.sort_values('distance', ignore_index=True) # sort the new df in order of appearance of the CoursePoints

    
xy=pd.to_datetime(gpxSpurdf.time, unit='s')
xy1=pd.to_timedelta(gpxSpurdf.time, unit='s')

# %%make a fit-file


def main():
    # Set auto_define to true, so that the builder creates the required Definition Messages for us.
    builder = FitFileBuilder(auto_define=True, min_string_size=50)

    message = FileIdMessage()
    message.type = FileType.COURSE
    message.manufacturer = Manufacturer.DEVELOPMENT.value
    message.product = 0
    message.time_created = round(datetime.datetime.now().timestamp() * 1000)
    message.serial_number = random.randint(1,1000000) # create a random number to act as serial_number
    message.number = 1
    builder.add(message)

    # Every FIT course file MUST contain a Course message
    message = CourseMessage()
    message.course_name = filename
    message.sport = Sport.CYCLING
    builder.add(message)

    # Every FIT course file MUST contain a Lap message

    message = LapMessage()
    message.timestamp = datetime.datetime.now().timestamp()*1000
    message.start_time = datetime.datetime.now().timestamp()*1000
    ii=gpxSpurdf.last_valid_index()
    message.total_distance = gpxSpurdf.distance[ii]
    builder.add(message)
    
    # Timer Events are REQUIRED for FIT course files
    start_timestamp = round(datetime.datetime.now().timestamp() * 1000)
    message = EventMessage()
    message.event = Event.TIMER
    message.event_type = EventType.START
    message.timestamp = start_timestamp
    message.event_group = 0
    builder.add(message)

    distance = 0.0
    timestamp = start_timestamp
    
    course_records = []  # track points

   
    for i in range(len(gpxSpurdf)):
        message = RecordMessage()
        message.position_lat = gpxSpurdf.latitude[i]
        message.position_long = gpxSpurdf.longitude[i]
        message.distance = gpxSpurdf.distance[i]
        message.timestamp=start_timestamp+round(gpxSpurdf.time[i])*1000
        message.enhanced_altitude = gpxSpurdf.elevation[i]
        course_records.append(message)
        timestamp = start_timestamp+round(gpxSpurdf.time[i])*1000
        builder.add(message)

        
    # Add start and end course points (i.e. way points)
    message = CoursePointMessage()
    message.timestamp = course_records[0].timestamp
    message.position_lat = course_records[0].position_lat
    message.position_long = course_records[0].position_long
    message.type = CoursePoint.SEGMENT_START
    message.course_point_name = 'start'
    builder.add(message)
    
    timestamp=start_timestamp
    for i in range(len(CoursePoints)): #loop over all course points and integrate them. create a message type for the specific course points. Will be glad if somebody can show me a more efficient way
        message = CoursePointMessage()
        message.timestamp=start_timestamp+round(CoursePoints.time[i]*1000)
        message.position_lat = CoursePoints.latitude[i]
        message.position_long = CoursePoints.longitude[i]
        if CoursePoints.type[i]=='WATER':
            message.type=CoursePoint.WATER
        elif CoursePoints.type[i]=='FOOD':
            message.type=CoursePoint.FOOD
        elif CoursePoints.type[i]=='AID_STATION':
            message.type=CoursePoint.FIRST_AID
        message.distance = CoursePoints.distance[i]
        message.course_point_name = CoursePoints.name[i]
        builder.add(message)

    message = CoursePointMessage()
    message.timestamp = course_records[-1].timestamp
    message.position_lat = course_records[-1].position_lat
    message.position_long = course_records[-1].position_long
    message.type = CoursePoint.SEGMENT_END
    message.course_point_name = 'end'
    builder.add(message)

    # stop event
    message = EventMessage()
    message.timestamp = timestamp
    message.event = Event.TIMER
    message.event_group = 0
    message.event_type = EventType.STOP_DISABLE_ALL
    builder.add(message)

    

    # Finally build the FIT file object and write it to a file
    fit_file = builder.build()
    out_path = filename+'.fit'
    fit_file.to_file(out_path)



if __name__ == "__main__":
    main()
    