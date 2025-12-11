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
from login_settings import get_settings

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Schedule station calibration observations in TMSS")
    parser.add_argument("-s", "--source", help="Source to observe [str, default: strategy default] (uses Simbad name resolver)",
                        default=None, type=str)
#    parser.add_argument("-a", "--antennafield", help="Antenna field to select [str, default: HBA_DUAL]",
#                        default="HBA_DUAL", type=str)
#    parser.add_argument("-f", "--filter", help="Filter to select [str, default: HBA_110_190]",
#                        default="HBA_110_190", type=str)
#    parser.add_argument("-t", "--tstart", help="Time between start (isot) [str, default: now]",
#                        default=None, type=str)
#    parser.add_argument("-w", "--window", help="Time between window length (d) [float, default: 1]",
#                        default=1.0, type=float)
    parser.add_argument("-L", "--stations", help="Station to use [str, default: strategy default, can be multiple, e.g. \"CS001,CS002,CS003\"]",
                        default=None, type=str)
#    parser.add_argument("-i", "--scheduling_set_id", help="Scheduling set ID [int, default: 395]",
#                        default=395, type=int)
    parser.add_argument("-M", "--description", help="Observation description [str, example \"HBA station calibration\", default: \"HBA station calibration\"]",
                        default="HBA station calibration", type=str)
#    parser.add_argument("-F", "--fixed_time", help="Fix observation start time (no dynamic scheduling)",
#                        action="store_true")
#    parser.add_argument("-S", "--subband", help="[Correlator] Subbands to select (e.g. '201..400', '128,256,384') [str, default: 201..400]",
#                        default="201..400", type=str)
#    parser.add_argument("-c", "--channels", help="[Correlator] Channels per subband [int, default: 64]",
#                        default=64, type=int)
#    parser.add_argument("-I", "--integration", help="[Correlator] Integration time [float, default: 1]",
#                        default=1, type=float)
#    parser.add_argument("-x", "--xst_subbands", help="[XST] Subband configuration [int, default: 0]",
#                        default=[0], nargs='+', type=int) 
#    parser.add_argument("-p", "--xst_subband_step", help="[XST] Subband step size per integration [int, default: 1]",
#                        default=1, type=int)
#    parser.add_argument("-T", "--xst_integration_time", help="[XST] Integration time per subband captured [float, default: 1.0]",
#                        default=1.0, type=float)
#    parser.add_argument("-N", "--xst_num_cycles", help="[XST] Number of full subband cycles [int, default 1]",
#                        default=1, type=int)
#    parser.add_argument("-C", "--cluster", help="Override cluster to record to (CEP4 or CEP6) [str, default: strategy default]",
#                        default=None, type=str)
#    parser.add_argument("-o", "--override_strategy", help="Use 'FE Stokes I - raw' instead of 'Simple Imaging Observation with preprocessing and XST settings' strategy",
#                        action="store_true")
    parser.add_argument("-V", "--strategy_version", help="Specify strategy version to use [int, default: None]",
                        default=None, type=int)
    parser.add_argument("-v", "--verbose", help="Provide detailed output",
                        action="store_true")
    parser.add_argument("-u", "--upload", help="Upload specification document and create scheduling unit draft",
                        action="store_true")
    parser.add_argument("-b", "--blueprint", help="Blueprint uploaded scheduling unit draft",
                        action="store_true")
    args = parser.parse_args()

    # Settings
    strategy_name = "HBA station calibration"
    description = args.description if args.description is not None else "Station calibration observation"

    # Get pointing
    if args.source is not None:
        p = get_icrs_coordinates(args.source)
        pointing = {"target": args.source,
                    "angle1": p.ra.rad,
                    "angle2": p.dec.rad,
                    "direction_type": "J2000"}

    # Stations
    if args.stations is not None:
        stations = args.stations.split(",")
        station_groups = [
            {
                "stations": stations,
                "max_nr_missing": len(stations) - 1
            }
        ] 
    
    # Read credentials
    settings = get_settings()

    # Set scheduling unit name
    su_name = f"{args.source} ({settings['username']})"
     
    # Open session
    with TMSSsession(host=settings['host'],
                     port=settings['port'],
                     username=settings['username'],
                     password=settings['password']) as client:
        print("Opened TMSS connection")
        
        # Get the latest satellite monitoring template
        template = client.get_scheduling_unit_observing_strategy_template(strategy_name, version=args.strategy_version)
        print(f"Using strategy template {template['url']}")
        
        # Get the specifications document
        original_spec_doc = client.get_scheduling_unit_observing_strategy_template_specification_with_just_the_parameters(template['name'], template['version'])

        # Copy original specification document
        spec_doc = original_spec_doc.copy()

        # Set pointings
        if args.source is not None:
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['station_configuration']['tile_beam'] = pointing
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['station_configuration']['SAPs'][0]['digital_pointing'] = pointing

        # Station groups
        if args.stations is not None:
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['beamformer']['pipelines'][0]['station_groups'] = station_groups
            spec_doc['tasks']['BackToDefault Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups
            spec_doc['tasks']['BackToDefault Observation']['specifications_doc']['beamformer']['pipelines'][0]['station_groups'] = station_groups

        # Show spec doc
        if args.verbose:
            print_dict(spec_doc, prefix="spec_doc")

        # Skip if not uploaded
        if not args.upload:
            print("No scheduling units uploaded to TMSS.")
            print()
            sys.exit()

        # Create scheduling unit
        scheduling_unit_draft = client.create_scheduling_unit_draft_from_strategy_template(template['id'], args.scheduling_set_id, spec_doc, su_name, description, src_spec['priority_queue'], src_spec['rank'])

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
        
