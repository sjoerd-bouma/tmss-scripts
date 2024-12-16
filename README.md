# TMSS Scripts

These are scripts for interfacing with the TMSS API.

- `run_script_fe.sh` runs the `tmss_fe_test_observation.py` using the `config_fe.yaml`
- `tmss_fe_test_observation.py` starts a Fly's Eye (FE) observation on one or more stations
- `run_script_im.sh` runs the `tmss_im_test_observation.py` using the `config_im.yaml`
- `tmss_im_test_observation.py` starts an imaging observation on one or more stations
- `tmss_list_scheduling_sets.py` lists all scheduling scheduling sets
- `tmss_list_strategies.py` lists all observing strategies
- `tmms_get_sasid.py` retrieves SASID for the given blueprint ID

Install the LOFAR TMSS client from https://git.astron.nl/ro/lofar_tmss_client

The scripts use a `login.yaml` file which should contain

Usage for testing:
./run_script_fe.sh -c config_fe.yaml
./run_script_im.sh -c config_im.yaml

Usage for uploading and/or blueprinting the SU:
./run_script_fe.sh -c config_fe.yaml --upload --blueprint
./run_script_im.sh -c config_im.yaml --upload --blueprint

```
username: username
password: password
host: path.to.tmss
port: port_number
```
