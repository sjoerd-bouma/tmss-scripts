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
    parser.add_argument("-a", "--antennafield", help="Antenna field to select [str, default: HBA_DUAL]",
                        default="HBA_DUAL", type=str)
    parser.add_argument("-f", "--filter", help="Filter to select [str, default: HBA_110_190]",
                        default="HBA_110_190", type=str)
    parser.add_argument("-t", "--tstart", help="Time between start (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-w", "--window", help="Time between window length (hours) [float, default: 24]",
                        default=24.0, type=float)
    parser.add_argument("-L", "--stations", help="Station to use [str, default: strategy default, can be multiple, e.g. \"CS001,CS002,CS003\"]",
                        default=None, type=str)
    parser.add_argument("-i", "--scheduling_set_id", help="Scheduling set ID [int, default: 395]",
                        default=395, type=int)
    parser.add_argument("-M", "--description", help="Observation description [str, example \"HBA station calibration\", default: \"HBA station calibration\"]",
                        default="HBA station calibration", type=str)
    parser.add_argument("-F", "--fixed_time", help="Fix observation start time (no dynamic scheduling)",
                        action="store_true")
    parser.add_argument("-x", "--xst_subbands", help="[XST] Subband configuration (e.g. 0 1 2 3 4 5 6) [list of ints, default: strategy default]",
                        default=None, nargs='+', type=int) 
    parser.add_argument("-p", "--xst_subband_step", help="[XST] Subband step size per integration [int, default: strategy default]",
                        default=None, type=int)
    parser.add_argument("-T", "--xst_integration_time", help="[XST] Integration time per subband captured [float, default: strategy default]",
                        default=None, type=float)
    parser.add_argument("-N", "--xst_num_cycles", help="[XST] Number of full subband cycles [int, default: strategy default]",
                        default=None, type=int)
    parser.add_argument("-V", "--strategy_version", help="Specify strategy version to use [int, default: None]",
                        default=None, type=int)
    parser.add_argument("-v", "--verbose", help="Provide detailed output",
                        action="store_true")
    parser.add_argument("-u", "--upload", help="Upload specification document and create scheduling unit draft",
                        action="store_true")
    parser.add_argument("-b", "--blueprint", help="Blueprint uploaded scheduling unit draft",
                        action="store_true")
    args = parser.parse_args()

    # Check if filter is compatible with antenna set
    if ("LBA" in args.filter and "HBA" in args.antennafield) or ("HBA" in args.filter and "LBA" in args.antennafield):
        print("Wrong combination of antennafield and filter selection. Exiting.")
        sys.exit()
    
    # Settings
    if "HBA" in args.antennafield:
        strategy_name = "HBA station calibration"
    elif "LBA" in args.antennafield:
        strategy_name = "LBA station calibration"
    description = args.description if args.description is not None else "Station calibration observation"

    # Start time
    if args.tstart is None:
        # Round to start of minute
        tstart = datetime.now(UTC)
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S")
    tend = tstart + timedelta(hours=args.window) 
    tstart = tstart.strftime("%Y-%m-%dT%H:%M:%S")
    tend = tend.strftime("%Y-%m-%dT%H:%M:%S")
    if args.fixed_time:
        tend = None
    
    # Get pointing
    if args.source is not None:
        source_name = args.source
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

    # Observation duration
    #if args.xst_subbands is not None and args.xst_integration_time is not None and args.xst_num_cycles is not None and args.xst_subband_step is not None:
    #    duration = int(ceil(args.xst_integration_time * 512 * args.xst_num_cycles / args.xst_subband_step))
    #else:
    #    duration = None

    # Read credentials
    settings = get_settings()

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

        # Get XST settings
        if args.xst_integration_time is None:
            xst_integration_time = spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['QA']['XST']['integration_interval']
        else:
            xst_integration_time = args.xst_integration_time
        if args.xst_subbands is None:
            xst_subbands = spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['QA']['XST']['subbands']
        else:
            xst_subbands = args.xst_subbands
        if args.xst_subband_step is None:
            xst_subband_step = spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['QA']['XST']['subbands_step']
        else:
            xst_subband_step = args.xst_subband_step
        if args.xst_num_cycles is None:
            duration = spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['duration']
            xst_num_cycles = round(duration * xst_subband_step / (512 * xst_integration_time))
        else:
            xst_num_cycles = args.xst_num_cycles

        # Compute duration
        duration = int(ceil(xst_integration_time * 512 * xst_num_cycles / xst_subband_step))
        
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

        # Filter/antenna field
        if args.antennafield is not None:
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['station_configuration']['antenna_set'] = args.antennafield
        if args.filter is not None:
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['station_configuration']['filter'] = args.filter

        # Set duration and XST settings
        if duration is not None:
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['duration'] = duration
            spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['QA']['XST'] = {"enabled": True,
                                                                                                       "integration_interval": args.xst_integration_time,
                                                                                                       "subbands": args.xst_subbands,
                                                                                                       "subbands_step": args.xst_subband_step}

        # Timing constraints
        if args.fixed_time:
            spec_doc['scheduling_constraints_doc']['time']['at'] = f'{tstart}'
            spec_doc['scheduling_constraints_doc']['scheduler'] = 'fixed_time'
        else:
            spec_doc['scheduling_constraints_doc']['time']['between'] = [{"from": tstart, "to": tend}]
            spec_doc['scheduling_constraints_doc']['scheduler'] = 'dynamic'

            
        # Show spec doc
        if args.verbose:
            print_dict(spec_doc, prefix="spec_doc")

        # Skip if not uploaded
        if not args.upload:
            print("No scheduling units uploaded to TMSS.")
            print()
            sys.exit()

        # Set scheduling unit name
        source_name = spec_doc['tasks']['Station Calibration Observation']['specifications_doc']['station_configuration']['tile_beam']['target']
        su_name = f"{source_name} ({settings['username']})"
        priority_queue = "A"
        rank = 1.00
            
        # Create scheduling unit
        scheduling_unit_draft = client.create_scheduling_unit_draft_from_strategy_template(template['id'], args.scheduling_set_id, spec_doc, su_name, description, priority_queue, rank)

        # Patch scheduling unit with keys that are not included in the strategy
        print(f"Created SU draft {scheduling_unit_draft['id']} for {source_name} at {scheduling_unit_draft['url']}")

        # Skip if not blueprinted
        if not args.blueprint:
            print("No scheduling units blueprinted.")
            print()
            sys.exit()

        # Blueprint SU
        scheduling_unit_blueprint = client.create_scheduling_unit_blueprint_and_tasks_and_subtasks_tree(scheduling_unit_draft['id'])
        print(f"Created SU blueprint {scheduling_unit_blueprint['id']} for {source_name} at {scheduling_unit_blueprint['url']}")
        
