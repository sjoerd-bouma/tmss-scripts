#!/usr/bin/env python3
import sys
import json
import yaml
from tmss_http_rest_client import TMSSsession

if __name__ == "__main__":
    # Read credentials
    with open("login.yaml", "r") as fp:
        settings = yaml.load(fp, Loader=yaml.FullLoader)

    # TMSS settings
    strategy_name = "BF Stokes I, satellite monitoring"
    host = "tmss.lofar.eu"
    port = 443
    
    with TMSSsession(host=host,
                     port=port,
                     username=settings["username"],
                     password=settings["password"]) as client:

        # Get the latest satellite monitoring template
        scheduling_sets = client.get_path_as_json_object("scheduling_set")

        for scheduling_set in scheduling_sets:
            print(f"{scheduling_set['id']:4d} | {scheduling_set['project_id']:20s} | {scheduling_set['name']} | {scheduling_set['description']}")
            
