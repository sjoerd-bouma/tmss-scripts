#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime, timedelta, UTC

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord

from print_dict import print_dict
from print_dict import replace_matching_values
from select_source import select_source, local_get_icrs_coordinates
from station_selection import get_station_selection
from login_settings import get_settings, get_tmss_session

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Schedule a pulsar observation.")
    parser.add_argument("-s", "--source", help="Source to observe [str, default: PSR B0329+54 (\"auto\" auto-select a source)] (uses Simbad name resolver)",
                        default="PSR B0329+54", type=str)
    parser.add_argument("-a", "--antennafield", help="Antenna field to select [str, default: HBA_DUAL]",
                        default="HBA_DUAL", type=str)
    parser.add_argument("-f", "--filter", help="Filter to select [str, default: HBA_110_190]",
                        default="HBA_110_190", type=str)
    parser.add_argument("-S", "--subband", help="Subbands to select (e.g. '201..400', '144*16', '128,256,384') [str, default: 51..450]",
                        default="51..450", type=str)
    parser.add_argument("-t", "--tstart", help="Start time (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-l", "--length", help="Observation length (s) [int, default: 60]",
                        default=60, type=int)
    parser.add_argument("-d", "--delay", help="Delay in scheduling (s) [int, default: 300]",
                        default=300, type=int)
    parser.add_argument("-L", "--stations", help="Stations to use [str (case insensitive), examples \"CS001,CS032,RS307\", \"Superterp\", \"ST\", \"Core\", \"CS\", \"Dutch\", \"RS\", \"Remote\", \"INT\", \"International\", \"All\", \"Full\", default: Core]",
                        default="Core", type=str)
    parser.add_argument("-i", "--scheduling_set_id", help="Scheduling set ID [int, default: 446]",
                        default=446, type=int)
    parser.add_argument("-M", "--description", help="Observation description [str, example \"Test observation\", default: None, will use \"Pulsar folding observation\"]",
                        default=None, type=str)
#    parser.add_argument("-X", "--xst", help="XST settings (subband start, subband step, integration time) [str, example: \"194,0,1.0\", default: None]",
#                        default=None, type=str)
    parser.add_argument("-C", "--constraints", help="Apply dynamic constraints from JSON file [file, default: none]",
                        default=None, metavar="FILE")
    parser.add_argument("-v", "--verbose", help="Provide detailed output",
                        action="store_true")
    parser.add_argument("-V", "--strategy_version", help="Specify strategy version to use [int, default: None]",
                        default=None, type=int)
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
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S")
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:%S")
    tend = datetime.strptime(tstart, "%Y-%m-%dT%H:%M:%S") + timedelta(days=1)
    tend = tend.strftime("%Y-%m-%dT%H:%M:%S")        
   
    # Get pointing
    source_name = args.source
    if source_name == "auto":
        source_name, p = select_source(tstart, "bf", args.filter[:3])
    else:
        p = local_get_icrs_coordinates(source_name)
    pointing = {"target": source_name,
                "angle1": float(p.ra.rad),
                "angle2": float(p.dec.rad),
                "direction_type": "J2000"}
    # Settings
    run_spec = {"strategy_name": "BF Pulsar Folding",
                "description": args.description if args.description is not None else "Pulsar folding observation"}
    src_spec = {"name": source_name,
                "elev_min_deg": 0,
                "lst_min_s": -43200,
                "lst_max_s": 43200,
                "priority_queue": "A",
                "rank": 1.00}

#    # Get XST settings
#    if args.xst is not None:
#        parts = args.xst.split(",")
#        xst_spec = {"enabled": True,
#                    "subbands": [int(parts[0])],
#                    "subbands_step": int(parts[1]),
#                    "integration_interval": float(parts[2])}
#    else:
#        xst_spec = {"enabled": False,
#                    "subbands": [300],
#                    "subbands_step": 0,
#                    "integration_interval": 1.0}
        
    # Decode subbands
    if "," in args.subband:
        subband_list = [int(part) for part in args.subband.split(",")]
    elif ".." in args.subband:
        smin = int(args.subband.split("..")[0])
        smax = int(args.subband.split("..")[-1])
        subband_list = list(range(smin, smax + 1))
    elif "*" in args.subband:
        subband = int(args.subband.split("*")[0])
        nsubband = int(args.subband.split("*")[1])
        subband_list = [subband] * nsubband
    else:
        subband_list = [int(args.subband)]

    # Station groups
    stations = get_station_selection(args.stations)
    station_groups = [{"stations": [item for item in stations],
                       "max_nr_missing": len(stations) - 1}]

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

    # Set scheduling unit name
    su_name = f"{source_name} ({settings['username']})"
    
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

        # Apply constraints
        if not constraints:
            spec_doc['scheduling_constraints_doc']['time']['at'] = f'{tstart}'
            spec_doc['scheduling_constraints_doc']['scheduler'] = 'fixed_time'
            spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['from'] = src_spec['lst_min_s']
            spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['to'] = src_spec['lst_max_s']
            for source_constraint in ['sun', 'moon', 'jupiter']:
                spec_doc['scheduling_constraints_doc']['sky']['min_distance']['target'][source_constraint] = 0
                spec_doc['scheduling_constraints_doc']['sky']['min_distance']['calibrator'][source_constraint] = 0            
        elif constraints:
            replace_matching_values(spec_doc, constraints)
            spec_doc['scheduling_constraints_doc']['scheduler'] = 'dynamic'
            spec_doc['scheduling_constraints_doc']['time']['between'] = [{"from": tstart, "to": tend}]

        spec_doc['tasks']['Observation']['specifications_doc']['duration'] = args.length
        spec_doc['tasks']['Observation']['short_description'] = src_spec["name"]
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['tile_beam'] = pointing
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['SAPs'][0]['digital_pointing'] = pointing
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['antenna_set'] = args.antennafield
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['filter'] = args.filter

        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups
        spec_doc['tasks']['Observation']['specifications_doc']['beamformer']['pipelines'][0]['station_groups'] = station_groups
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['SAPs'][0]['subbands'] = subband_list
        #spec_doc['tasks']['Observation']['specifications_doc']['beamformer']['pipelines'][0]['coherent']['SAPs'][0]['subbands']['list'] = subband_list
#        if xst_spec["enabled"]:
#            spec_doc['tasks']['Observation']['specifications_doc']['QA']['XST'] = xst_spec

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
        
