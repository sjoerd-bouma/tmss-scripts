#!/usr/bin/env python3
import yaml

from lofar_tmss_client.tmss_http_rest_client import TMSSsession
from login_settings import get_settings

if __name__ == "__main__":
    # Read credentials
    settings = get_settings()

    with TMSSsession(host=settings["host"],
                     port=settings["port"],
                     username=settings["username"],
                     password=settings["password"]) as client:

        # Get the latest satellite monitoring template
        templates = client.get_scheduling_unit_observing_strategy_templates()

        for template in templates:
            print(f"{template['id']:4d} | {template['name']} | v{template['version']} | {template['state_value']}")
            
