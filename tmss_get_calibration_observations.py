#!/usr/bin/env python3
import sys
import json
import yaml
import argparse

from print_dict import print_dict
from datetime import datetime, timedelta, UTC

from login_settings import get_settings, get_tmss_session

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="List tasks")
    parser.add_argument("-s", "--tstart", help="Start time (isot) [str, default: now - 25h]",
                        default=None, type=str)
    parser.add_argument("-e", "--tend", help="Start time (isot) [str, default: now - 1h]",
                        default=None, type=str)
    parser.add_argument("-o", "--output", help="Output to file (json) instead of screen) [str, default: None]",
                        default=None, type=str)
    args = parser.parse_args()

    subtask_type = "observation"
    
    # Start time
    if args.tstart is None and args.tend is None:
        tstart = (datetime.now(UTC) + timedelta(hours=-25)).strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
        tend = (datetime.now(UTC) + timedelta(hours=-1)).strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
        tend = datetime.strptime(args.tend, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")

    # Read credentials
    settings = get_settings()

    with get_tmss_session(settings) as client:

        # Format URL
        url = f"https://tmss.lofar.eu/api/subtask?state__value=&cluster__name=&cluster__name__icontains=&id=&id_min=&id_max=&state=finished&name=&error_reason=&on_sky_start_time__lt=&on_sky_start_time__gt={tstart}&on_sky_stop_time__lt={tend}&on_sky_stop_time__gt=&process_start_time__lt=&process_start_time__gt=&process_stop_time__lt=&process_stop_time__gt=&scheduled_start_time__lt=&scheduled_start_time__gt=&scheduled_stop_time__lt=&scheduled_stop_time__gt=&actual_on_sky_start_time__lt=&actual_on_sky_start_time__gt=&actual_on_sky_stop_time__lt=&actual_on_sky_stop_time__gt=&actual_process_start_time__lt=&actual_process_start_time__gt=&actual_process_stop_time__lt=&actual_process_stop_time__gt=&project=Calibration&subtask_type={subtask_type}&is_using_lofar2_stations=unknown&is_using_any_lofar2_stations=unknown&is_obsolete=unknown"

        # Query results
        spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=url)

        # Loop over results
        results = []
        for o in spec_doc["results"]:
            duration = float(o['on_sky_duration'])
            task_type = o['subtask_type']
            obsid = o['id']
            tstart = o['actual_on_sky_start_time'].replace("Z", "")
            tend = o['actual_on_sky_stop_time'].replace("Z", "")
            band = o['specifications_doc']['stations']['filter']
            antennaset = o['specifications_doc']['stations']['antenna_set']
            stations = o['specifications_doc']['stations']['station_list']
            duration = o['on_sky_duration']
            
            # Skip if no XST recording specified
            if not o['specifications_doc']['QA']['XST']['enabled']:
                continue
            # Skip on bad XST subbands_step
            if o['specifications_doc']['QA']['XST']['subbands_step'] == 0:
                continue

            results.append(o)
            if args.output is None:
                print(f"| {obsid} | {task_type} | {tstart} | {duration:6.0f} | {antennaset:8s} | {band:11s} | {len(stations)}")

        # Write selected observations
        if args.output is not None:
            with open(args.output, "w") as fp:
                json.dump(results, fp)
                
