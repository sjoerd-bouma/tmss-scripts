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
        templates = client.get_scheduling_unit_observing_strategy_templates()

        for template in templates:
            print(f"{template['id']:4d} | {template['name']} | v{template['version']} | {template['state_value']}")
            
