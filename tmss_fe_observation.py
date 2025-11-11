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
    parser = argparse.ArgumentParser(description="Schedule a Fly's Eye observation.")
    parser.add_argument("-s", "--source", help="Source to observe [str, default: PSR B0329+54] (uses Simbad name resolver)",
                        default="PSR B0329+54", type=str)
    parser.add_argument("-a", "--antennafield", help="Antenna field to select [str, default: HBA_DUAL]",
                        default="HBA_DUAL", type=str)
    parser.add_argument("-f", "--filter", help="Filter to select [str, default: HBA_110_190]",
                        default="HBA_110_190", type=str)
    parser.add_argument("-S", "--subband", help="Subbands to select (e.g. '201..400', '144*16', '128,256,384') [str, default: 201..400]",
                        default="201..400", type=str)
    parser.add_argument("-t", "--tstart", help="Start time (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-l", "--length", help="Observation length (s) [int, default: 60]",
                        default=60, type=int)
    parser.add_argument("-d", "--delay", help="Delay in scheduling (s) [int, default: 300]",
                        default=300, type=int)
    parser.add_argument("-L", "--stationlist", help="Station to use [str, default: CS001, can be multiple, e.g. \"CS001,CS002,CS003\"]",
                        default="CS001", type=str)
    parser.add_argument("-i", "--scheduling_set_id", help="Scheduling set ID [int, default: 432]",
                        default=305, type=int)
    parser.add_argument("-p", "--pointings", help="Override source pointing (can be multiple) [str, example: \"Zenith,0.0,1.5707963,AZELGEO\", default: None]",
                        default=None, type=str, action="append")
    parser.add_argument("-m", "--mode", help="Observing mode (I, IQUV or XXYY) [str, default: I]",
                        default="I", type=str)
    parser.add_argument("-D", "--downsamp", help="Downsampling factor for Stokes I observing [int, default: 16]",
                        default=16, type=int)
    parser.add_argument("-c", "--channels", help="Channels per subband for Stokes I observing [int, default: 16]",
                        default=16, type=int)
    parser.add_argument("-n", "--saps", help="Number of identical sub-array pointings (SAPs) [int, default: 1]",
                        default=1, type=int)
    parser.add_argument("-N", "--subbands_per_file", help="Number of subbands per file [int, default: 488 for mode I, 20 for mode XX]",
                        default=None, type=int)
    parser.add_argument("-M", "--description", help="Observation description [str, example \"Test observation\", default: None, will use \"Fly's Eye observation\"]",
                        default=None, type=str)
    parser.add_argument("-X", "--xst", help="XST settings (subband start, subband step, integration time) [str, example: \"194,0,1.0\", default: None]",
                        default=None, type=str)
    parser.add_argument("-1", "--missing_station", help="Allows each station to be missed from the observation",
                        action="store_true")
    parser.add_argument("-C", "--cluster", help="Override cluster to record to (CEP4 or CEP6) [str, default: strategy default]",
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

    # Settings
    run_spec = {"strategy_name": "FE Stokes I - raw",
                "description": args.description if args.description is not None else "Fly's Eye observation"}
    src_spec = {"name": args.source,
                "elev_min_deg": 0,
                "lst_min_s": -43200,
                "lst_max_s": 43200,
                "priority_queue": "A",
                "rank": 1.00}

    # Get pointing
    if args.pointings is None:
        p = get_icrs_coordinates(args.source)
        pointings = [{"target": args.source,
                      "angle1": p.ra.rad,
                      "angle2": p.dec.rad,
                      "direction_type": "J2000"}]
        tile_pointing = pointings[0]
    else:
        pointings = []
        first = True
        for point in args.pointings:
            parts = point.split(",")
            pointing = {"target": parts[0],
                        "angle1": float(parts[1]),
                        "angle2": float(parts[2]),
                        "direction_type": parts[3]}
            if first:
                src_spec["name"] = parts[0]
                tile_pointing = pointing
                first = False
            pointings.append(pointing)

    # Get XST settings
    if args.xst is not None:
        parts = args.xst.split(",")
        xst_spec = {"enabled": True,
                    "subbands": [int(parts[0])],
                    "subbands_step": int(parts[1]),
                    "integration_interval": float(parts[2])}
    else:
        xst_spec = {"enabled": False,
                    "subbands": [300],
                    "subbands_step": 0,
                    "integration_interval": 1.0}
        
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

    # Start time
    if args.tstart is None:
        # Round to start of minute
        tstart = datetime.now(UTC) + timedelta(seconds=args.delay)
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:00")
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S")
        tstart = tstart.strftime("%Y-%m-%dT%H:%M:%S")

    # Station groups for Fly's Eye observations
    stationlist = [item for item in args.stationlist.split(",")]
    if args.missing_station:
        station_groups = [{"stations": [item for item in stationlist],
                           "max_nr_missing": len(stationlist) - 1}]
    else:
        station_groups = [{"stations": [item],
                           "max_nr_missing": 0} for item in stationlist]

    # Check if filter is compatible with antenna set
    if ("LBA" in args.filter and "HBA" in args.antennafield) or ("HBA" in args.filter and "LBA" in args.antennafield):
        print("Wrong combination of antennafield and filter selection. Exiting.")
        sys.exit()

    # Check if total number of subbands fits
    if len(subband_list) * len(pointings) * args.saps > 488:
        print("Too many subbands per pointing specified. Exiting.")
        sys.exit()
        
    # Subbands per file
    if args.subbands_per_file is not None:
        subbands_per_file = args.subbands_per_file
    else:
        if args.mode == "XXYY":
            subbands_per_file = 20
        elif args.mode == "I":
            subbands_per_file = 488
        elif args.mode == "IQUV":
            subbands_per_file = 488
            
    # Observing modes
    if args.mode == "XXYY":
        mode = {"stokes": "XXYY",
                "quantisation": {
                    "bits": 8,
                    "enabled": False,
                    "scale_max": 5,
                    "scale_min": -5,
                },
                "subbands_per_file": subbands_per_file,
                "channels_per_subband": 1,
                "time_integration_factor": 1
                }
    elif args.mode == "I":
        mode =  {"stokes": "I",
                 "quantisation": {
                     "bits": 8,
                     "enabled": False,
                     "scale_max": 5,
                     "scale_min": -5,
                 },
                 "subbands_per_file": subbands_per_file,
                 "channels_per_subband": args.channels,
                 "time_integration_factor": args.downsamp
                 }
    elif args.mode == "IQUV":
        mode =  {"stokes": "IQUV",
                 "quantisation": {
                     "bits": 8,
                     "enabled": False,
                     "scale_max": 5,
                     "scale_min": -5,
                 },
                 "subbands_per_file": subbands_per_file,
                 "channels_per_subband": args.channels,
                 "time_integration_factor": args.downsamp
                 }
        
            
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
        saps = []
        idx = 0
        for pointing in pointings:
            for isap in range(args.saps):
                sap = {
                    "name": f"SAP{idx:03d}",
                    "subbands": subband_list,
                    "digital_pointing": pointing
                }
                saps.append(sap)
                idx += 1
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['SAPs'] = saps
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['tile_beam'] = tile_pointing
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['antenna_set'] = args.antennafield
        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['filter'] = args.filter

        spec_doc['tasks']['Observation']['specifications_doc']['station_configuration']['station_groups'] = station_groups
        spec_doc['tasks']['Observation']['specifications_doc']['beamformer']['pipelines'][0]['station_groups'] = station_groups
        spec_doc['tasks']['Observation']['specifications_doc']['beamformer']['pipelines'][0]['flys eye']['settings'] = mode
        if args.cluster is not None:
            spec_doc['tasks']['Observation']['specifications_doc']['beamformer']['storage_cluster'] = args.cluster
        if xst_spec["enabled"]:
            spec_doc['tasks']['Observation']['specifications_doc']['QA']['XST'] = xst_spec

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
        
