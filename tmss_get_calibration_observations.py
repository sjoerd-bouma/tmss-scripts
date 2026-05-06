#!/usr/bin/env python3
import sys
import json
import yaml
import argparse

from datetime import datetime, timedelta, UTC

from login_settings import get_settings, get_tmss_session

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="List tasks")
    parser.add_argument("-p", "--project", help="Project to which tasks belong [str, default: COM_LOFAR2]",
                        default="Calibration", type=str)
    parser.add_argument("-s", "--tstart", help="Start time (isot) [str, default: now - 1 day]",
                        default=None, type=str)
    parser.add_argument("-e", "--tend", help="Start time (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-o", "--output", help="Output to file (json) instead of screen) [str, default: None]",
                        default=None, type=str)
    args = parser.parse_args()

    subtask_type = "observation"
    
    # Start time
    if args.tstart is None and args.tend is None:
        tstart = (datetime.now(UTC) + timedelta(days=-1)).strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
        tend = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
        tend = datetime.strptime(args.tend, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")

    # Read credentials
    settings = get_settings()

    with get_tmss_session(settings) as client:

        # Format URL
        #url = f"https://tmss.lofar.eu/api/task_blueprint?tags=&created_at_after=&created_at_before=&updated_at_after=&updated_at_before=&name=&description=&scheduled_start_time_after={tstart}&scheduled_start_time_before={tend}&scheduled_stop_time_after=&scheduled_stop_time_before=&actual_process_start_time_after=&actual_process_start_time_before=&actual_process_stop_time_after=&actual_process_stop_time_before=&actual_on_sky_start_time_after=&actual_on_sky_start_time_before=&actual_on_sky_stop_time_after=&actual_on_sky_stop_time_before=&process_start_time_after=&process_start_time_before=&process_stop_time_after=&process_stop_time_before=&on_sky_start_time_after=&on_sky_start_time_before=&on_sky_stop_time_after=&on_sky_stop_time_before=&on_sky_duration=&duration=&specified_on_sky_duration=&obsolete_since=&short_description=&specifications_doc=&specifications_template=&draft=&scheduling_unit_blueprint=&output_pinned=unknown&id=&id_min=&id_max=&scheduling_unit_blueprint_min=&scheduling_unit_blueprint_max=&scheduling_unit_blueprint_name=&scheduling_set_name=&project={args.project}&draft_min=&draft_max=&duration_min=&duration_max=&on_sky_duration_min=&on_sky_duration_max=&relative_start_time_min=&relative_start_time_max=&relative_stop_time_min=&relative_stop_time_max=&subtasks_min=&subtasks_max=&obsolete=&task_type={task_type}"

        url = f"https://tmss.lofar.eu/api/subtask?state__value=&cluster__name=&cluster__name__icontains=&id=&id_min=&id_max=&state=finished&name=&error_reason=&on_sky_start_time__lt=&on_sky_start_time__gt={tstart}&on_sky_stop_time__lt={tend}&on_sky_stop_time__gt=&process_start_time__lt=&process_start_time__gt=&process_stop_time__lt=&process_stop_time__gt=&scheduled_start_time__lt=&scheduled_start_time__gt=&scheduled_stop_time__lt=&scheduled_stop_time__gt=&actual_on_sky_start_time__lt=&actual_on_sky_start_time__gt=&actual_on_sky_stop_time__lt=&actual_on_sky_stop_time__gt=&actual_process_start_time__lt=&actual_process_start_time__gt=&actual_process_stop_time__lt=&actual_process_stop_time__gt=&project={args.project}&subtask_type={subtask_type}&is_using_lofar2_stations=unknown&is_using_any_lofar2_stations=unknown&is_obsolete=unknown"
        # Query results
        spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=url)

        # Open file
        if args.output is not None:
            with open(args.output, "w") as fp:
                json.dump(spec_doc["results"], fp)
                
        # Print results
        for o in spec_doc["results"]:
            duration = float(o['on_sky_duration'])
            task_type = o['subtask_type']
            obsid = o['id']
            tstart = o['actual_on_sky_start_time'].replace("Z", "")
            tend = o['actual_on_sky_stop_time'].replace("Z", "")
            band = o['specifications_doc']['stations']['filter']
            antennaset = o['specifications_doc']['stations']['antenna_set']
            stations = o['specifications_doc']['stations']['station_list']

            if args.output is None:
                for station in stations:
                    if "HBA" in antennaset:
                        if "CS" in station:
                            antenna_fields = ["HBA0", "HBA1"]
                        else:
                            antenna_fields = ["HBA"]
                    elif "LBA" in antennaset:
                        antenna_fields = ["LBA"]
                    for antenna_field in antenna_fields:
                        cmd = f"bash pipeline.sh L{obsid} {tstart} {tend} {station} {antenna_field}"
                        print(cmd)
