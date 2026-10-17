#!/usr/bin/env python3
import os
import sys
import yaml
import argparse
from datetime import datetime, timedelta, UTC

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord, get_icrs_coordinates

from print_dict import print_dict
from station_selection import get_station_selection
from login_settings import get_settings, get_tmss_session

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Test a strategy.")
    parser.add_argument("-S", "--strategy", help="Name (str) of strategy to observe [str, default: None]",
                        default=None, type=str)
    parser.add_argument("-t", "--tstart", help="Start time (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-l", "--length", help="Observation length (s) [int, default: 60]",
                        default=60, type=int)
    parser.add_argument("-d", "--delay", help="Delay in scheduling (s) [int, default: 300]",
                        default=300, type=int)
    parser.add_argument("-i", "--scheduling_set_id", help="Scheduling set ID [int, default: 446]",
                        default=358, type=int)
    parser.add_argument("-M", "--description", help="Observation description [str, example \"Test observation\", default: None, will use \"Strategy test\"]",
                        default=None, type=str)
    parser.add_argument("-V", "--strategy_version", help="Specify strategy version to use [int, default: None]",
                        default=None, type=int)
    parser.add_argument("-v", "--verbose", help="Provide detailed output",
                        action="store_true")
    parser.add_argument("-u", "--upload", help="Upload specification document and create scheduling unit draft",
                        action="store_true")
    parser.add_argument("-b", "--blueprint", help="Blueprint uploaded scheduling unit draft",
                        action="store_true")
    args = parser.parse_args()

    # Check strategy
    if args.strategy is None:
        print("Provide strategy name")
        sys.exit()
    
    # Settings
    run_spec = {"strategy_name": args.strategy,
                "description": args.description if args.description is not None else "Strategy test"}
    src_spec = {"name": "Strategy test",
                "elev_min_deg": 0,
                "lst_min_s": -43200,
                "lst_max_s": 43200,
                "priority_queue": "A",
                "rank": 1.00}

    # Start time
    if args.tstart is None:
        # Round to start of minute
        tstart = datetime.now(UTC) + timedelta(seconds=args.delay)
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:00")
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S")
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:%S")

    # Read credentials
    settings = get_settings()

    # Set scheduling unit name
    su_name = f"Strategy test ({settings['username']})"
    
    # Open session
    with get_tmss_session(settings) as client:
        print("Opened TMSS connection")
        
        # Get the template
        template = client.get_scheduling_unit_observing_strategy_template(run_spec['strategy_name'], version=args.strategy_version)
        print(f"Using strategy template {template['url']}")

        # Get the specifications document
        original_spec_doc = client.get_scheduling_unit_observing_strategy_template_specification_with_just_the_parameters(template['name'], template['version'])

        # Copy original specification document
        spec_doc = original_spec_doc.copy()
        
        spec_doc['scheduling_constraints_doc']['time']['at'] = f'{tstart}'
        spec_doc['scheduling_constraints_doc']['scheduler'] = 'fixed_time'
        spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['from'] = src_spec['lst_min_s']
        spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['to'] = src_spec['lst_max_s']
        for source_constraint in ['sun', 'moon', 'jupiter']:
            spec_doc['scheduling_constraints_doc']['sky']['min_distance']['target'][source_constraint] = 0
            spec_doc['scheduling_constraints_doc']['sky']['min_distance']['calibrator'][source_constraint] = 0            

        spec_doc['tasks']['Observation']['specifications_doc']['duration'] = args.length
        spec_doc['tasks']['Observation']['short_description'] = src_spec["name"]

        # Show spec doc
        if args.verbose:
            print_dict(spec_doc, prefix="spec_doc")
           
        # Skip if not uploaded
        if not args.upload:
            print("No scheduling units uploaded to TMSS.")
            print()
            sys.exit()

        # Create scheduling unit
        scheduling_unit_draft = client.create_scheduling_unit_draft_from_strategy_template(template['id'], args.scheduling_set_id, spec_doc, su_name, run_spec['description'], src_spec['priority_queue'], src_spec['rank'])

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
        
