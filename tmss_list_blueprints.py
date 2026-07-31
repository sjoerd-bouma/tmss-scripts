#!/usr/bin/env python3
import sys
import json
import yaml
import argparse

from termcolor import colored

import numpy as np

from print_dict import print_dict
from datetime import datetime, timedelta, UTC

from login_settings import get_settings, get_tmss_session

def set_length(s, nchar):
    length = len(s)
    if length < nchar:
        for i in range(nchar - length):
            s+= " "
    else:
        s = s[:nchar-3] + "..."
            
    return s    

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="List tasks")
    parser.add_argument("-p", "--project", help="Project to which tasks belong [str, default: None]",
                        default=None, type=str)
    parser.add_argument("-s", "--tstart", help="Start time (isot) [str, default: now - 1 day]",
                        default=None, type=str)
    parser.add_argument("-e", "--tend", help="Start time (isot) [str, default: now]",
                        default=None, type=str)
    parser.add_argument("-O", "--observation", help="Status of observation task [str, default: none]",
                        default=None, type=str)
    parser.add_argument("-P", "--pipeline", help="Status of pipeline task [str, default: none]",
                        default=None, type=str)
    parser.add_argument("-I", "--ingest", help="Status of ingest task [str, default: none]",
                        default=None, type=str)
    parser.add_argument("-C", "--cleanup", help="Status of cleanup task [str, default: none]",
                        default=None, type=str)
    parser.add_argument("-i", "--id", help="Select on blueprint ID [int, default: none]",
                        default=None, type=int)
    parser.add_argument("-n", "--name", help="Select on (part of string) in SU name [str, default: none]",
                        default=None, type=str)
    parser.add_argument("-d", "--description", help="Select on (part of string) in SU description [str, default: none]",
                        default=None, type=str)
    parser.add_argument("-o", "--only", help="Only print selected blueprints",
                        action="store_true")
    parser.add_argument("-u", "--unpin", help="Unpin blueprint to run clean up task",
                        action="store_true")
    parser.add_argument("--cancel_pipeline", help="Cancel pipeline task",
                        action="store_true")
    parser.add_argument("--cancel_ingest", help="Cancel ingest task",
                        action="store_true")
    parser.add_argument("--obsolete_pipeline", help="Obsolete pipeline task",
                        action="store_true")
    parser.add_argument("--obsolete_ingest", help="Obsolete ingest task",
                        action="store_true")
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
        url = f"https://tmss.lofar.eu/api/scheduling_unit_blueprint_slim_with_tasks?on_sky_start_time_after={tstart}&on_sky_start_time_before={tend}&ordering=on_sky_start_time"
        if args.project is not None:
            url += f"&project={args.project}"
        if args.id is not None:
            url += f"&id={args.id}"

        # Query results
        results = client.get_url_as_json_object(full_url=url)

        # Color definition
        states = ["finished", "error", "schedulable", "unschedulable", "observed", "cancelled", "started", "scheduled", "queued", "defined", "on hold"]
        statecolors = ["green", "red", "blue", (135, 206, 235), "green", (255, 165, 0), "yellow", (0, 0, 100), "cyan", "magenta", "light_red"]
        
        # Loop over results to generate output dictionary
        output_results = []
        for i, o in enumerate(results):
            station_spec = set_length(f"{len(o['used_stations']):2d} {o['antenna_set']}", 14)
            project = set_length(o["project"], 12)
            s = f"{o['id']:5d} | {project} | {o['on_sky_start_time']} | {o['on_sky_duration'][:8]} | {station_spec} "
            for task_type, abbrev, in zip(["observation", "pipeline", "ingest", "cleanup"], ["O", "P", "I", "C"]):
                found = False
                for task in o["task_blueprints"]:
                    if task['task_type'] == task_type:
                        status = task['status']
                        if status not in states:
                            print(status)
                        for state, statecolor in zip(states, statecolors):
                            if status == state:
                                state_string = colored(set_length(status, 15), statecolor)
                                found = True

                if found:
                    stmp = f"| {abbrev}: {state_string}"
                else:
                    stmp = set_length("|", 15 + 5)
                s += stmp
            name = set_length(o['name'], 30)
            description = set_length(o['description'], 30)
            s += f"| {name}  | {description}"

            # Store output
            output_results.append({"line": s,
                                   "tasks": [{task['task_type']: task['status']} for task in o["task_blueprints"]],
                                   "task_info": [{"task_type": task["task_type"], "status": task["status"], "id": task["id"]} for task in o["task_blueprints"]],
                                   "id": o["id"],
                                   "name": o["name"],
                                   "description": o["description"]}
                                  )
        # Specify selected lines
        task_selections = [False for result in output_results]

        # Define task states
        task_states = []
        if args.observation is not None:
            task_states.append({"observation": args.observation})
        if args.pipeline is not None:
            task_states.append({"pipeline": args.pipeline})
        if args.ingest is not None:
            task_states.append({"ingest": args.ingest})
        if args.cleanup is not None:
            task_states.append({"cleanup": args.cleanup})

        # Apply selections
        if len(task_states) > 0:
            for i, result in enumerate(output_results):
                tasks = result["tasks"]
                if all(item in tasks for item in task_states):
                    task_selections[i] = True

        # Select on name
        name_selections = [False for result in output_results]
        if args.name is not None:
            for i, result in enumerate(output_results):
                if args.name in result["name"]:
                    name_selections[i] = True

        # Select on description
        description_selections = [False for result in output_results]
        if args.description is not None:
            for i, result in enumerate(output_results):
                if args.description in result["description"]:
                    description_selections[i] = True

        # Combine selections
        lists = [task_selections]
        if args.name is not None:
            lists.append(name_selections)
        if args.description is not None:
            lists.append(description_selections)
        selections = [all(values) for values in zip(*lists)]
                    
        # Print results to screen
        for selection, result in zip(selections, output_results):
            line = result["line"]
            if selection:
                print(f"[X]| {line}")
            elif not args.only:
                print(f"[ ]| {line}")

        # Return selected blueprints
        if sum(selections) > 0:
            print(f"Selected {sum(selections)} blueprints")
                
        # Unpin selected blueprints
        if args.unpin:
            bpids = [result["id"] for result, selection in zip(output_results, selections) if selection]
            for bpid in bpids:
                result = client.set_scheduling_unit_blueprint_pinning(bpid, False)
                print(f"Unpinned blueprint ID {bpid}")

        # Cancel pipelines of selected blueprints
        if args.cancel_pipeline:
            for selection, r in zip(selections, output_results):
                if selection:
                    for task in r["task_info"]:
                        if task["task_type"] == "pipeline":
                            result = client.cancel_task_blueprint(task["id"])
                            print(f"Cancelling pipeline task blueprint ID {task['id']}")

        # Cancel ingest of selected blueprints
        if args.cancel_ingest:
            for selection, r in zip(selections, output_results):
                if selection:
                    for task in r["task_info"]:
                        if task["task_type"] == "ingest":
                            result = client.cancel_task_blueprint(task["id"])
                            print(f"Cancelling ingest task blueprint ID {task['id']}")

        # Obsolete pipelines of selected blueprints
        if args.obsolete_pipeline:
            for selection, r in zip(selections, output_results):
                if selection:
                    for task in r["task_info"]:
                        if task["task_type"] == "pipeline":
                            result = client.mark_task_blueprint_as_obsolete(task["id"])
                            print(f"Obsoleting pipeline task blueprint ID {task['id']}")

        # Obsolete ingest of selected blueprints
        if args.obsolete_ingest:
            for selection, r in zip(selections, output_results):
                if selection:
                    for task in r["task_info"]:
                        if task["task_type"] == "ingest":
                            result = client.mark_task_blueprint_as_obsolete(task["id"])
                            print(f"Obsoleting ingest task blueprint ID {task['id']}")

                            
