#!/usr/bin/env python3
import yaml

from lofar_tmss_client.tmss_http_rest_client import TMSSsession

from login_settings import get_settings

if __name__ == "__main__":
    # Read credentials
    settings = get_settings()

    # TMSS settings
    with TMSSsession(host=settings["host"],
                     port=settings["port"],
                     username=settings["username"],
                     password=settings["password"]) as client:

        # Get the latest satellite monitoring template
        scheduling_sets = client.get_path_as_json_object("scheduling_set")

        for scheduling_set in scheduling_sets:
            print(f"{scheduling_set['id']:4d} | {scheduling_set['project_id']:20s} | {scheduling_set['name']} | {scheduling_set['description']}")
            
