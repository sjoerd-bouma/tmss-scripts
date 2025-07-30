# TMSS Scripts

These are scripts for interfacing with the TMSS API.

- `tmss_fe_observation.py` starts a Fly's Eye (FE) observation on one or more stations
- `tmss_im_observation.py` starts an interferometric observation on one or more stations
- `tmss_list_scheduling_sets.py` lists all scheduling scheduling sets
- `tmss_list_strategies.py` lists all observing strategies
- `tmms_get_sasid.py` retrieves SASID for the given blueprint ID
- `script/run_script_fe.sh` runs the `tmss_fe_test_observation.py` using the `config_fe.yaml`
- `script/run_script_im.sh` runs the `tmss_im_test_observation.py` using the `config_im.yaml`

Install the LOFAR TMSS client from https://git.astron.nl/tmss/lofar_tmss_client

Usage for testing:
./script/run_script_fe.sh -c config/config_fe.yaml
./script/run_script_im.sh -c config/config_im.yaml

Usage for uploading and/or blueprinting the SU:
./script/run_script_fe.sh -c config/config_fe.yaml --upload --blueprint
./script/run_script_im.sh -c config/config_im.yaml --upload --blueprint

The scripts use a `login.yaml` file which should contain a username, host and port. The
password field is optional, and can be removed or set to "null" to be prompted at runtime
for the value, or hardcoded within the file.

```
username: username
password: null
host: tmss.lofar.eu
port: 443
```
