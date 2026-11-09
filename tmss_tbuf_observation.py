#!/usr/bin/env python3
import sys
import json
import argparse
from datetime import datetime, timedelta, UTC

import numpy as np

from print_dict import print_dict
from print_dict import replace_matching_values
from station_selection import get_station_selection
from login_settings import get_settings, get_tmss_session

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Schedule a TBuf observation.")
    parser.add_argument("-a", "--antennafield", help="Antenna field to select [str, default: LBA_ALL]",
                        default="LBA_ALL", type=str)
    parser.add_argument("-f", "--filter", help="Filter to select [str, default: LBA_10_90]",
                        default="LBA_10_90", type=str)
    parser.add_argument("-t", "--tstart", help="Start time (isot) [str, default: now]; also accepts \"dynamic\" to use the dynamic scheduler",
                        default=None, type=str)
    parser.add_argument("-l", "--length", help="Observation length (s) [int, default: 3600]",
                        default=3600, type=int)
    parser.add_argument("-d", "--delay", help="Delay in scheduling (s) [int, default: 300]",
                        default=300, type=int)
    parser.add_argument("-L", "--stations", help="Stations to use [str (case insensitive), examples \"CS001,CS032,RS307\", \"Superterp\", \"ST\", \"Core\", \"CS\", \"Dutch\", \"RS\", \"Remote\", \"INT\", \"International\", \"All\", \"Full\", default: Dutch]",
                        default="Dutch", type=str)
    parser.add_argument("-i", "--scheduling_set_id",
                        help="Scheduling set ID [int, default: None]; accepted L2CC_012 values are 472 (single station), 473 (Dutch stations) or 474 (All stations). If None, attempts to automatically determine based on station set.",
                        default=None, type=int)
    parser.add_argument("-m", "--missing_stations", help="Specify number of stations that can be missed [int, default: 50%% of all stations]",
                        default=None, type=int)
    parser.add_argument("-M", "--description", help="Observation description [str, example \"Test observation\", default: None, will \"Test observation\"]",
                        default=None, type=str)
    parser.add_argument("-C", "--constraints", help="Apply dynamic constraints from JSON file [file, default: none]",
                    default=None, metavar="FILE")
    parser.add_argument("-v", "--verbose", help="Provide detailed output",
                        action="store_true")
    parser.add_argument("-u", "--upload", help="Upload specification document and create scheduling unit draft",
                        action="store_true")
    parser.add_argument("-b", "--blueprint", help="Blueprint uploaded scheduling unit draft",
                        action="store_true")
    args = parser.parse_args()

    # Start time
    if args.tstart is None:
        # Round to start of minute
        tstart = datetime.now(UTC) + timedelta(seconds=args.delay)
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:00")
    elif args.tstart.lower() == 'dynamic':
        tstart = None
        tend = None
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S")
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:%S")

    if tstart is not None:
        tend = datetime.strptime(tstart, "%Y-%m-%dT%H:%M:%S") + timedelta(days=1)
        tend = tend.strftime("%Y-%m-%dT%H:%M:%S")

    # Settings
    run_spec = {"strategy_name": "LIFT",
                "description": args.description if args.description is not None else "TBuf test observation"}
    src_spec = {"name": "LIFT Test Observation",
                "priority_queue": "A",
                "rank": 1.00}

    # Stations
    stations = get_station_selection(args.stations)
    if args.missing_stations is not None:
        missing_stations = args.missing_stations
    else:
        missing_stations = min(len(stations)-1, max(1, int(np.ceil(0.5 * len(stations)))))
    station_groups = [
        {
            "stations": stations, 
            "max_nr_missing": missing_stations
        }
    ]

    scheduling_set_id = args.scheduling_set_id
    if scheduling_set_id is None: # attempt to determine automatically
        if args.stations.lower() == 'dutch':
            scheduling_set_id = 473
        elif args.stations.lower() in ['full', 'all']:
            scheduling_set_id = 474
        elif len(stations) == 1: # single station observation
            scheduling_set_id = 472
        else:
            raise ValueError("\"scheduling_set_id\" could not be determined from station set, please specify manually")

    # Check if filter is compatible with antenna set
    if ("LBA" in args.filter and "HBA" in args.antennafield) or ("HBA" in args.filter and "LBA" in args.antennafield):
        print("Wrong combination of antennafield and filter selection. Exiting.")
        sys.exit()     

    # Constraints
    if args.constraints is not None:
        try:
            with open(args.constraints, "r") as fp:
                constraints = json.load(fp)
        except json.decoder.JSONDecodeError as e:
            print(f"JSON decoder error {e}. Exiting.")
            sys.exit()     
        except FileNotFoundError:
            print("JSON file with constraints not found. Exiting.")
            sys.exit()     

    # Read credentials
    settings = get_settings()

    # Open session
    with get_tmss_session(settings) as client:
        print("Opened TMSS connection")
        
        # Get the template
        template = client.get_scheduling_unit_observing_strategy_template(run_spec['strategy_name'])
        print(f"Using strategy template {template['url']}")
        
        # Get the specifications document
        original_spec_doc = client.get_scheduling_unit_observing_strategy_template_specification_with_just_the_parameters(
            template['name'], template['version'])

        # Copy original specification document
        spec_doc = original_spec_doc.copy()

        # Apply constraints
        if args.constraints is None:
            if tstart is not None:
                spec_doc['scheduling_constraints_doc']['time']['at'] = f'{tstart}'
                spec_doc['scheduling_constraints_doc']['scheduler'] = 'fixed_time'
            else:
                spec_doc['scheduling_constraints_doc']['scheduler'] = 'dynamic'
        else:
            replace_matching_values(spec_doc, constraints)
            spec_doc['scheduling_constraints_doc']['scheduler'] = 'dynamic'
            spec_doc['scheduling_constraints_doc']['time']['between'] = [{"from": tstart, "to": tend}]
        
        spec_doc['tasks']['Observation']['specifications_doc']['duration'] = args.length
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['antenna_set'] = args.antennafield
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['filter'] = args.filter
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups

        # Show spec doc
        if args.verbose:
            print_dict(spec_doc, prefix="spec_doc")

        # Skip if not uploaded
        if not args.upload:
            print("No scheduling units uploaded to TMSS.")
            print()
            sys.exit()

        su_name = f"{src_spec['name']} ({settings['username']})"

        scheduling_unit_draft = client.create_scheduling_unit_draft_from_strategy_template(
            template['id'], parent_scheduling_set_id=scheduling_set_id,
            specifications_doc_overrides=spec_doc,
            name=su_name, description=run_spec['description'],
            priority_queue=src_spec['priority_queue'], rank=src_spec['rank'])

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
