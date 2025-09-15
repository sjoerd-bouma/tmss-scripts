#!/usr/bin/env python3
import sys
import yaml
import argparse

from lofar_tmss_client.tmss_http_rest_client import TMSSsession

from print_dict import print_dict
from login_settings import get_settings

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Get blueprint ID from the subtask ID (SASID)")
    parser.add_argument("subtask_id", help="Subtask ID [int]",
                        default=None, type=int)
    args = parser.parse_args()

    # Read credentials
    settings = get_settings()
    
    with TMSSsession(host=settings['host'],
                     port=settings['port'],
                     username=settings['username'],
                     password=settings['password']) as client:

        # Get subtask specdoc
        url = f"https://{settings['host']}/api/subtask/{args.subtask_id}"
        subtask_spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=url)

        # Get task specdoc
        task_specdoc = client.do_request_and_get_result_as_json_object(method="GET", full_url=subtask_spec_doc["task_blueprint"])

        # Get blueprint ID
        blueprint_id = task_specdoc["scheduling_unit_blueprint_id"]
        blueprint = task_specdoc["scheduling_unit_blueprint"]
        print(f"{args.subtask_id} -> {blueprint_id} | {blueprint} | https://{settings['host']}/schedulingunit/view/blueprint/{blueprint_id}")

        
