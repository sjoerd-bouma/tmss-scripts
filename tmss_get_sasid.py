#!/usr/bin/env python3
import sys
import yaml

from lofar_tmss_client.tmss_http_rest_client import TMSSsession

from print_dict import print_dict
from login_settings import get_settings

if __name__ == "__main__":
    blueprint_id = int(sys.argv[1])
    
    # Read credentials
    settings = get_settings()
    
    with TMSSsession(host=settings['host'],
                     port=settings['port'],
                     username=settings['username'],
                     password=settings['password']) as client:

        # Get SU blueprint
        url = f"https://{settings['host']}/api/scheduling_unit_blueprint/{blueprint_id}"
        spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=url)

        # Loop over task blueprints
        for task_url in spec_doc["task_blueprints"]:
            spec_doc = client.do_request_and_get_result_as_json_object(method="GET", full_url=task_url)
            if spec_doc["name"] == "Observation":
                print(spec_doc["subtasks_ids"], spec_doc["name"])
