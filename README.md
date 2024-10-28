# TMSS Scripts

These are scripts for interfacing with the TMSS API.

- `tmss_fe_test_observation.py` starts a Fly's Eye (FE) observation on one or more stations
- `tmss_list_scheduling_sets.py` lists all scheduling scheduling sets
- `tmss_list_strategies.py` lists all observing strategies
- `tmms_get_sasid.py` retrieves SASID for the given blueprint ID

Install the LOFAR TMSS client from https://git.astron.nl/ro/lofar_tmss_client

The scripts use a `login.yaml` file which should contain
```
username: username
password: password
host: path.to.tmss
port: port_number
```
