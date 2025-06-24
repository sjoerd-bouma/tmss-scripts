#!/usr/bin/env python3
import os
import sys
import yaml
import json
import argparse
from datetime import datetime, timedelta, UTC
from math import ceil

import astropy.units as u
from astropy.coordinates import SkyCoord, get_icrs_coordinates

from lofar_tmss_client.tmss_http_rest_client import TMSSsession

from print_dict import print_dict

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Schedule station calibration observations in TMSS")
    parser.add_argument("-s", "--source", help="Source to observe [str, default: Cas A]",
                        default="Cas A", type=str)
    parser.add_argument("-a", "--antennafield", help="Antenna field to select [str, default: HBA_DUAL]",
                        default="HBA_DUAL", type=str)
    parser.add_argument("-f", "--filter", help="Filter to select [str, default: HBA_110_190]",
                        default="HBA_110_190", type=str)
    parser.add_argument("-t", "--tstart", help="Time between start (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-w", "--window", help="Time between window length (d) [float, default: 1]",
                        default=1.0, type=float)
    parser.add_argument("-L", "--stationlist", help="Station to use [str, default: CS001, can be multiple, e.g. \"CS001,CS002,CS003\"]",
                        default="CS001", type=str)
    parser.add_argument("-i", "--scheduling_set_id", help="Scheduling set ID [int, default: 395]",
                        default=395, type=int)
    parser.add_argument("-M", "--description", help="Observation description [str, example \"HBA station calibration\", default: \"HBA station calibration\"]",
                        default="HBA station calibration", type=str)
    parser.add_argument("-v", "--verbose", help="Provide detailed output",
                        action="store_true")
    parser.add_argument("-F", "--fixed_time", help="Fix observation start time (no dynamic scheduling)",
                        action="store_true")
    parser.add_argument("-u", "--upload", help="Upload specification document and create scheduling unit draft",
                        action="store_true")
    parser.add_argument("-b", "--blueprint", help="Blueprint uploaded scheduling unit draft",
                        action="store_true")
    parser.add_argument("-S", "--subbands", help="Inital subband configuration",
                        default=[0], nargs='+', type=int)
    parser.add_argument("-p", "--subband_step", help="Subband step size per integration",
                        default=1, type=int)
    parser.add_argument("-T", "--integration_time", help="Integration time per subband captured",
                        default=1.0, type=float)
    parser.add_argument("-N", "--num_cycles", help="Number of full subband cycles",
                        default=1.0, type=float)
    args = parser.parse_args()

    # Settings
    run_spec = {"strategy_name": "FE Stokes I - raw",
                "description": args.description}
    if args.fixed_time:
        src_spec = {"name": args.source,
                    "elev_min_deg": 00,
                    "lst_min_s": -43200,
                    "lst_max_s": 43200,
                    "priority_queue": "A",
                    "rank": 1.00}
    else:
        src_spec = {"name": args.source,
                    "elev_min_deg": 30,
                    "lst_min_s": -7200,
                    "lst_max_s": 7200,
                    "priority_queue": "A",
                    "rank": 1.00}

    # Get pointing
    p = get_icrs_coordinates(args.source)
    pointing = {"target": args.source,
                "angle1": p.ra.rad,
                "angle2": p.dec.rad,
                "direction_type": "J2000"}
                
    # Start time
    if args.tstart is None:
        # Round to start of minute
        tstart = datetime.now(UTC)
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S")
    tend = tstart + timedelta(days=args.window) 
    tstart = tstart.strftime("%Y-%m-%dT%H:%M:%S")
    tend = tend.strftime("%Y-%m-%dT%H:%M:%S")
        
    # Station groups for Fly's Eye observations
    stationlist = [item for item in args.stationlist.split(",")]
    station_groups = [{"stations": [item],
                       "max_nr_missing": 1} for item in stationlist]

    # Check antenna field against LOFAR2.0 stations
    if args.antennafield == "LBA_ALL":
        if not set(stationlist) <= set(["CS001", "CS032", "RS307"]):
            print("Can not use LBA_ALL on LOFAR stations. Exiting.")
            sys.exit()

    # Check if filter is compatible with antenna set
    if ("LBA" in args.filter and "HBA" in args.antennafield) or ("HBA" in args.filter and "LBA" in args.antennafield):
        print("Wrong combination of antennafield and filter selection. Exiting.")
        sys.exit()

    observation_time = int(ceil(args.integration_time * 512 * args.num_cycles / args.subband_step))
    # Specify observing mode
    mode =  {"stokes": "I",
             "quantisation": {
                 "bits": 8,
                 "enabled": False,
                 "scale_max": 5,
                 "scale_min": -5,
             },
             "subbands_per_file": 488,
             "channels_per_subband": 16,
             "time_integration_factor": 512
             }
        
    # Read credentials
    with open("login.yaml", "r") as fp:
        settings = yaml.full_load(fp)

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

        if args.fixed_time:
            spec_doc['scheduling_constraints_doc']['time']['at'] = f'{tstart}'
            spec_doc['scheduling_constraints_doc']['scheduler'] = 'fixed_time'
        else:
            spec_doc['scheduling_constraints_doc']['time']['between'] = [{"from": tstart, "to": tend}]
            spec_doc['scheduling_constraints_doc']['scheduler'] = 'dynamic'
        spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['from'] = src_spec['lst_min_s']
        spec_doc['scheduling_constraints_doc']['sky']['transit_offset']['to'] = src_spec['lst_max_s']

        spec_doc['tasks']['Observation']['specifications_doc']['duration'] = observation_time
        spec_doc['tasks']['Observation']['short_description'] = src_spec["name"]
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['SAPs'] = [{"subbands": [200],
                                                                                                   "digital_pointing": pointing}]
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['tile_beam'] = pointing
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['antenna_set'] = args.antennafield
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['filter'] = args.filter

        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups
        spec_doc['tasks']['Observation']['specifications_doc']['beamformer']['pipelines'][0]['station_groups'] = station_groups
        spec_doc['tasks']['Observation']['specifications_doc']['beamformer']['pipelines'][0]['flys eye']['settings'] = mode

        spec_doc['tasks']['Observation']['specifications_doc']['QA']['XST'] = {"enabled": True,
                                                                               "integration_interval": args.integration_time,
                                                                               "subbands": args.subbands,
                                                                               "subbands_step": args.subband_step}

        # Show spec doc
        if args.verbose:
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
        
