#!/usr/bin/env python3
import sys
import json
import yaml
import argparse

from datetime import datetime, timedelta, UTC

from lofar_tmss_client.tmss_http_rest_client import TMSSsession

from print_dict import print_dict

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="List tasks")
    parser.add_argument("-p", "--project", help="Project to which tasks belong [str, default: COM_LOFAR2]",
                        default="COM_LOFAR2", type=str)
    parser.add_argument("-s", "--tstart", help="Start time (isot) [str, default: now - 1 day]",
                        default=None, type=str)
    parser.add_argument("-e", "--tend", help="Start time (isot) [str, default: now]",
                        default=None, type=str)
    args = parser.parse_args()

    task_type = "observation"
    
    # Start time
    if args.tstart is None and args.tend is None:
        tstart = (datetime.now(UTC) + timedelta(days=-1)).strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
        tend = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
    else:
        tstart = datetime.strptime(args.tstart, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")
        tend = datetime.strptime(args.tend, "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S").replace(":", "%3A")

    # Read credentials
    with open("login.yaml", "r") as fp:
        settings = yaml.load(fp, Loader=yaml.FullLoader)

    with TMSSsession(host=settings['host'],
                     port=settings['port'],
                     username=settings['username'],
                     password=settings['password']) as client:

        # Format URL
        url = f"https://tmss.lofar.eu/api/task_blueprint?tags=&created_at_after=&created_at_before=&updated_at_after=&updated_at_before=&name=&description=&scheduled_start_time_after={tstart}&scheduled_start_time_before={tend}&scheduled_stop_time_after=&scheduled_stop_time_before=&actual_process_start_time_after=&actual_process_start_time_before=&actual_process_stop_time_after=&actual_process_stop_time_before=&actual_on_sky_start_time_after=&actual_on_sky_start_time_before=&actual_on_sky_stop_time_after=&actual_on_sky_stop_time_before=&process_start_time_after=&process_start_time_before=&process_stop_time_after=&process_stop_time_before=&on_sky_start_time_after=&on_sky_start_time_before=&on_sky_stop_time_after=&on_sky_stop_time_before=&on_sky_duration=&duration=&specified_on_sky_duration=&obsolete_since=&short_description=&specifications_doc=&specifications_template=&draft=&scheduling_unit_blueprint=&output_pinned=unknown&id=&id_min=&id_max=&scheduling_unit_blueprint_min=&scheduling_unit_blueprint_max=&scheduling_unit_blueprint_name=&scheduling_set_name=&project={args.project}&draft_min=&draft_max=&duration_min=&duration_max=&on_sky_duration_min=&on_sky_duration_max=&relative_start_time_min=&relative_start_time_max=&relative_stop_time_min=&relative_stop_time_max=&subtasks_min=&subtasks_max=&obsolete=&task_type={task_type}"

        # Query results
        spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=url)

        #print(f"|| OBSID || BP ID || Task || Start || Duration || Antenna Set || Band || Description | Stations |")

        #print_dict(spec_doc, prefix="spec_doc")
        
        # Print results
        for o in spec_doc["results"]:
#            print(o)
            blueprint_id = o['scheduling_unit_blueprint_id']
            description = o['short_description']
            duration = o['specifications_doc']['duration']
            task_type = o['task_type']
            obsid = o['subtasks_ids'][0]
            tstart = o['scheduled_start_time']
            band = o['specifications_doc']['station_configuration']['filter']
            antennaset = o['specifications_doc']['station_configuration']['antenna_set']
            station_groups = o['specifications_doc']['station_configuration']['station_groups']
            stations = [s for sg in station_groups for s in sg['stations']]
            #print(f"| {obsid} | {blueprint_id} | {task_type} | {tstart} | {duration:6d} | {antennaset:8s} | {band:11s} | {description} | {stations}")

            # Create station string
            station_string = ""
            for station in stations:
                station_string += f"{station} "
            station_string = station_string.rstrip()
            
            if "LBA" in antennaset:
                cmd = f"python l2json/quick_impl.py --tstart {tstart} --duration {duration} --output_pattern \"/home/bassa/calibration/{{start}}_L{obsid}_{{station}}{{field}}_{{datatype}}.h5\" --station {station_string} --type XST --field LBA"
            elif "HBA_DUAL" in antennaset:
                cmd = f"python l2json/quick_impl.py --tstart {tstart} --duration {duration} --output_pattern \"/home/bassa/calibration/{{start}}_L{obsid}_{{station}}{{field}}_{{datatype}}.h5\" --station {station_string} --type XST --field HBA0 HBA1 HBA"
            print(cmd)
