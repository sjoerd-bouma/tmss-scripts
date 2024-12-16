# TMSS Scripts

These are scripts for interfacing with the TMSS API.

- `tmss_fe_observation.py` starts a Fly's Eye (FE) observation on one or more stations
- `tmss_im_observation.py` starts an interferometric observation on one or more stations
- `tmss_list_scheduling_sets.py` lists all scheduling scheduling sets
- `tmss_list_strategies.py` lists all observing strategies
- `tmms_get_sasid.py` retrieves SASID for the given blueprint ID
- `script/run_script_fe.sh` runs the `tmss_fe_test_observation.py` using the `config_fe.yaml`
- `script/run_script_im.sh` runs the `tmss_im_test_observation.py` using the `config_im.yaml`

Install the LOFAR TMSS client from https://git.astron.nl/ro/lofar_tmss_client

The scripts use a `login.yaml` file which should contain

Usage for testing:
./script/run_script_fe.sh -c config/config_fe.yaml
./script/run_script_im.sh -c config/config_im.yaml

Usage for uploading and/or blueprinting the SU:
./script/run_script_fe.sh -c config/config_fe.yaml --upload --blueprint
./script/run_script_im.sh -c config/config_im.yaml --upload --blueprint

```
username: username
password: password
host: path.to.tmss
port: port_number
```
