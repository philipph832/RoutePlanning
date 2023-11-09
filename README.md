# RoutePlanning

This code is dedicated to perform several steps on a gpx-file
1) perform overpass-querries to identify certain points (mostly amenities along a given route). Routes need to be in gpx-format and can be created and downloaded from any route-planning app/website.
2) safe these new points as Waypoints in a new gpx-file
3) plot the track and waypoints on a map
4) integrate the new waypoints as Course Points into the track (for creating a garmin-compatible fit file)
5) correctly calculate distances and time between the points
6) write evrything into a garmin fit-file to be used for navigation on any garmin device. This will finally show the course points and trigger a warning 100m before you reach the point.

Overall this shall help planning outdoor activities by finding water and other intersting (or necessary) stops. On the gps-device the user will then see the distance to these points and can plan the ride/run in a better fashion. 

It is hand-made by a non-coder. Any help for simplification and increasing efficiency and flexibility of the code is highly welcome and appreciated!
