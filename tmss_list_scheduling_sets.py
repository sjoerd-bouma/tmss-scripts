#!/usr/bin/env python3
import yaml

from login_settings import get_settings, get_tmss_session

if __name__ == "__main__":
    # Read credentials
    settings = get_settings()

    # TMSS settings
    with get_tmss_session(settings) as client:

        # Get the latest satellite monitoring template
        scheduling_sets = client.get_path_as_json_object("scheduling_set")

        for scheduling_set in scheduling_sets:
            print(f"{scheduling_set['id']:4d} | {scheduling_set['project_id']:20s} | {scheduling_set['name']} | {scheduling_set['description']}")
            
