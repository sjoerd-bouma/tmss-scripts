#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
from datetime import datetime, timedelta, UTC

import astropy.units as u
from astropy.coordinates import SkyCoord, get_icrs_coordinates

from lofar_tmss_client.tmss_http_rest_client import TMSSsession

from print_dict import print_dict
from login_settings import get_settings

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Schedule an imaging observation.")
    parser.add_argument("-s", "--source", help="Source to observe [str, default: Cas A] (uses Simbad name resolver)",
                        default="Cas A", type=str)
    parser.add_argument("-a", "--antennafield", help="Antenna field to select [str, default: HBA_DUAL]",
                        default="HBA_DUAL", type=str)
    parser.add_argument("-f", "--filter", help="Filter to select [str, default: HBA_110_190]",
                        default="HBA_110_190", type=str)
    parser.add_argument("-S", "--subband", help="Subbands to select (e.g. '201..400', '128,256,384') [str, default: 201..400]",
                        default="201..400", type=str)
    parser.add_argument("-t", "--tstart", help="Start time (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-l", "--length", help="Observation length (s) [int, default: 60]",
                        default=60, type=int)
    parser.add_argument("-d", "--delay", help="Delay in scheduling (s) [int, default: 300]",
                        default=300, type=int)
    parser.add_argument("-L", "--stations", help="Stations to use [str, default: CS001,CS032,RS307]",
                        default="CS001,CS032,RS307", type=str)
    parser.add_argument("-i", "--scheduling_set_id", help="Scheduling set ID [int, default: 345]",
                        default=345, type=int)
    parser.add_argument("-p", "--pointing", help="Override source pointing [str, example: \"Zenith,0.0,1.5707963,AZELGEO\", default: None]",
                        default=None, type=str)
    parser.add_argument("-c", "--channels", help="Channels per subband [int, default: 64]",
                        default=64, type=int)
    parser.add_argument("-I", "--integration", help="Integration time [float, default: 1]",
                        default=1, type=float)
    parser.add_argument("-u", "--upload", help="Upload specification document and create scheduling unit draft",
                        action="store_true")
    parser.add_argument("-b", "--blueprint", help="Blueprint uploaded scheduling unit draft",
                        action="store_true")
    args = parser.parse_args()

    # Settings
    run_spec = {"strategy_name": "Simple Imaging Observation with preprocessing",
                "description": "L2TS test observation"}
    src_spec = {"name": args.source,
                "elev_min_deg": 0,
                "lst_min_s": -43200,
                "lst_max_s": 43200,
                "priority_queue": "A",
                "rank": 1.00}

    # Get pointing
    if args.pointing is None:
        p = get_icrs_coordinates(args.source)
        pointing = {"target": args.source,
                    "angle1": p.ra.rad,
                    "angle2": p.dec.rad,
                    "direction_type": "J2000"}

    else:
        parts = args.pointing.split(",")
        pointing = {"target": parts[0],
                    "angle1": float(parts[1]),
                    "angle2": float(parts[2]),
                    "direction_type": parts[3]}
        src_spec["name"] = parts[0]

    # Decode subbands
    if "," in args.subband:
        subband_list = [int(part) for part in args.subband.split(",")]
    elif ".." in args.subband:
        smin = int(args.subband.split("..")[0])
        smax = int(args.subband.split("..")[-1])
        subband_list = list(range(smin, smax + 1))
    else:
        subband_list = [int(args.subband)]
        
    # Start time
    if args.tstart is None:
        # Round to start of minute
        tstart = datetime.now(UTC) + timedelta(seconds=args.delay)
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:00")
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S")
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:%S")
    
    # Stations
    stations = args.stations.split(",")
    station_groups = [
        {
            "stations": stations, 
            "max_nr_missing": 0  
        }
    ]
    
    # Check if filter is compatible with antenna set
    if ("LBA" in args.filter and "HBA" in args.antennafield) or ("HBA" in args.filter and "LBA" in args.antennafield):
        print("Wrong combination of antennafield and filter selection. Exiting.")
        sys.exit()     
            
    # Read credentials
    settings = get_settings()

    # Open session
    with TMSSsession(host=settings['host'],
                     port=settings['port'],
                     username=settings['username'],
                     password=settings['password']) as client:
        print("Opened TMSS connection")
        
        # Get the latest satellite monitoring template
        template = client.get_scheduling_unit_observing_strategy_template(run_spec['strategy_name'])
        print(f"Using strategy template {template['url']}")
        
        # Get the specifications document
        original_spec_doc = client.get_scheduling_unit_observing_strategy_template_specification_with_just_the_parameters(template['name'], template['version'])

        # Copy original specification document
        spec_doc = original_spec_doc.copy()
        
        spec_doc['scheduling_constraints_doc']['time']['at'] = f'{tstart}'
        spec_doc['scheduling_constraints_doc']['scheduler'] = 'fixed_time'
        spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['from'] = src_spec['lst_min_s']
        spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['to'] = src_spec['lst_max_s']

        spec_doc['tasks']['Observation']['specifications_doc']['duration'] = args.length
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['SAPs'][0]['subbands'] = subband_list
        spec_doc['tasks']['Observation']['short_description'] = src_spec["name"]
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['tile_beam'] = pointing
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['SAPs'][0]['digital_pointing'] = pointing
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['antenna_set'] = args.antennafield
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['filter'] = args.filter
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups
        spec_doc['tasks']['Observation']['specifications_doc']['correlator']['integration_time'] = args.integration
        spec_doc['tasks']['Observation']['specifications_doc']['correlator']['channels_per_subband'] = args.channels



        # Show spec doc
        print_dict(spec_doc, prefix="spec_doc")

        # Skip if not uploaded
        if not args.upload:
            print("No scheduling units uploaded to TMSS.")
            print()
            sys.exit()

        # Create scheduling unit
        scheduling_unit_draft = client.create_scheduling_unit_draft_from_strategy_template(template['id'], args.scheduling_set_id, spec_doc, src_spec["name"], run_spec['description'], src_spec['priority_queue'], src_spec['rank'])

        # Patch scheduling unit with keys that are not included in the strategy
        print(f"Created SU draft {scheduling_unit_draft['id']} for {src_spec['name']} at {scheduling_unit_draft['url']}")

        # Skip if not blueprinted
        if not args.blueprint:
            print("No scheduling units blueprinted.")
            print()
            sys.exit()

        # Blueprint SU
        scheduling_unit_blueprint = client.create_scheduling_unit_blueprint_and_tasks_and_subtasks_tree(scheduling_unit_draft['id'])
        print(f"Created SU blueprint {scheduling_unit_blueprint['id']} for {src_spec['name']} at {scheduling_unit_blueprint['url']}")
        
