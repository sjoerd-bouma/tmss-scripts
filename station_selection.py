#!/usr/bin/env python3

def get_station_selection(stations):
    # Specific station selections
    st_stations = ["CS002", "CS003", "CS004", "CS005", "CS006", "CS007"]
    cs_stations = ["CS001", "CS002", "CS003", "CS004", "CS005", "CS006",
                   "CS007", "CS011", "CS013", "CS017", "CS021", "CS024",
                   "CS026", "CS028", "CS030", "CS031", "CS032", "CS101",
                   "CS103", "CS201", "CS301", "CS302", "CS401", "CS501"]
    rs_stations = ["RS106", "RS205", "RS208", "RS210", "RS305", "RS306",
                   "RS307", "RS310", "RS406", "RS407", "RS409", "RS503",
                   "RS508", "RS509"]
    int_stations = ["DE601", "DE602", "DE603", "DE604", "DE605", "FR606",
                    "SE607", "UK608", "DE609", "PL610", "PL611", "PL612",
                    "IE613", "LV614"] #, "IT615", "BG616"]
    dutch_stations = cs_stations + rs_stations
    all_stations = dutch_stations + int_stations

    # Fixed mappings
    station_map = [
        (["st", "superterp"], st_stations),
        (["cs", "core"], cs_stations),
        (["rs", "remote"], rs_stations),
        (["int", "international"], int_stations),
        (["dutch", "cs+rs"], dutch_stations),
        (["all", "full"], all_stations),
    ]
    for keys, value in station_map:
        if stations.lower() in keys:
            return value

    # Specific selection
    input_stations = stations.split(",")
    stations = [station for station in input_stations if station in all_stations]
    
    return stations
