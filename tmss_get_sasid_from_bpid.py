#!/usr/bin/env python3
import sys
import yaml
import argparse

from lofar_tmss_client.tmss_http_rest_client import TMSSsession

from print_dict import print_dict
from login_settings import get_settings

if __name__ == "__main__":
    # Read command line arguments
    parser = argparse.ArgumentParser(description="Get subtask ID (SASID) from blueprint ID")
    parser.add_argument("blueprint_id", help="Blueprint id [int]",
                        default=None, type=int)
    args = parser.parse_args()

    # Read credentials
    settings = get_settings()
    
    with TMSSsession(host=settings['host'],
                     port=settings['port'],
                     username=settings['username'],
                     password=settings['password']) as client:

        # Get SU blueprint
        url = f"https://{settings['host']}/api/scheduling_unit_blueprint/{args.blueprint_id}"
        spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=url)

        # Loop over task blueprints
        for task_url in spec_doc["task_blueprints"]:
            spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=task_url)
            print(spec_doc["subtasks_ids"], spec_doc["name"])
