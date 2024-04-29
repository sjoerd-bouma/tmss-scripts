# TMSS Scripts

These are scripts for interfacing with the TMSS API.

- `tmss_fe_test_observation.py` starts a Fly's Eye (FE) observation on one or more stations
- `tmss_list_scheduling_sets.py` lists all scheduling scheduling sets
- `tmss_list_strategies.py` lists all observing strategies

The scripts use a `login.yaml` file which should contain
```
username: username
password: password
host: path.to.tmss
port: port_number
```
