# TMSS Scripts

These are scripts for interfacing with the TMSS API.

Observation scripts:
- `tmss_fe_observation.py` starts a Fly's Eye (FE) observation
- `tmss_im_observation.py` starts an interferometric observation
- `tmss_bf_observation.py` starts a beamformed observation
- `tmss_psr_observation.py` starts a beamformed pulsar observation (with pipeline)
- `tmss_cal_observation.py` starts a station calibration observation

Query scripts:
- `tmss_list_scheduling_sets.py` lists all scheduling scheduling sets
- `tmss_list_strategies.py` lists all observing strategies
- `tmss_get_sasid_from_bpid.py` retrieves SASIDs for the given blueprint ID
- `tmss_get_bpid_from_sasid.py` retreives blueprint ID for the given SASID
- `tmss_list_blueprints.py` lists blueprints based on CLI selection criteria

Install the LOFAR TMSS client from https://git.astron.nl/tmss/lofar_tmss_client

The scripts use a `login.yaml` file which should contain a TMSS token, host and port.
```
token: 
host: tmss.lofar.eu
port: 443
```
