#!/bin/bash

# Usage for testing:
# ./run_script_fe.sh -c config_fe.yaml

# Usage when immediately uploading and/or blueprinting the SU:
# ./run_script_fe.sh -c config_fe.yaml --upload --blueprint

# Default values
CONFIG_FILE=""
UPLOAD_FLAG=""
BLUEPRINT_FLAG=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -c|--config) CONFIG_FILE="$2"; shift ;;
        --upload) UPLOAD_FLAG="-u" ;;  # Set upload flag
        --blueprint) BLUEPRINT_FLAG="-b" ;;  # Set blueprint flag
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Check if configuration file is provided
if [[ -z "$CONFIG_FILE" ]]; then
    echo "Error: Configuration file is required (-c|--config)"
    exit 1
fi


# Check if yq is installed for parsing YAML
if ! command -v yq &> /dev/null; then
    echo "Error: yq is not installed. Please install it (e.g., 'sudo apt install yq' or 'brew install yq')."
    exit 1
fi

# Extract parameters from the YAML file
SOURCE=$(yq e '.source' "$CONFIG_FILE")
ANTENNAFIELD=$(yq e '.antennafield' "$CONFIG_FILE")
FILTER=$(yq e '.filter' "$CONFIG_FILE")
SUBBAND=$(yq e '.subband' "$CONFIG_FILE")
LENGTH=$(yq e '.length' "$CONFIG_FILE")
DELAY=$(yq e '.delay' "$CONFIG_FILE")
STATIONLIST=$(yq e '.stationlist' "$CONFIG_FILE")
SCHEDULING_SET_ID=$(yq e '.scheduling_set_id' "$CONFIG_FILE")
MODE=$(yq e '.mode' "$CONFIG_FILE")
DOWNSAMP=$(yq e '.downsamp' "$CONFIG_FILE")
CHANNELS=$(yq e '.channels' "$CONFIG_FILE")
SAPS=$(yq e '.saps' "$CONFIG_FILE")
TSTART_LIST=$(yq e '.tstart[]' "$CONFIG_FILE")

# Optional parameters
# Override pointing [str, example: "Zenith,0.0,1.5707963,AZELGEO"]
POINTING=$(yq e '.pointing // ""' "$CONFIG_FILE")
# Number of subbands per file [int, default: 488 for mode I, 20 for mode XX]
SUBBANDS_PER_FILE=$(yq e '.subbands_per_file // ""' "$CONFIG_FILE")

# Run tmss_fe_observation.py for each tstart value
while IFS= read -r TSTART; do
    if [[ -n "$TSTART" ]]; then
        # Construct the Python command
        CMD="python tmss_fe_observation.py \
            -s \"$SOURCE\" \
            -a \"$ANTENNAFIELD\" \
            -f \"$FILTER\" \
            -S \"$SUBBAND\" \
            -t \"$TSTART\" \
            -l \"$LENGTH\" \
            -d \"$DELAY\" \
            -L \"$STATIONLIST\" \
            -i \"$SCHEDULING_SET_ID\" \
            -m \"$MODE\" \
            -D \"$DOWNSAMP\" \
            -c \"$CHANNELS\" \
            -n \"$SAPS\""

            # Include optional parameters if they are provided
            if [[ -n "$POINTING" ]]; then
                CMD+=" -p \"$POINTING\""
            fi
            if [[ -n "$SUBBANDS_PER_FILE" ]]; then
                CMD+=" -N \"$SUBBANDS_PER_FILE\""
            fi
                        
            if [[ -n "$UPLOAD_FLAG" ]]; then
                CMD+=" $UPLOAD_FLAG"
            fi
            if [[ -n "$BLUEPRINT_FLAG" ]]; then
                CMD+=" $BLUEPRINT_FLAG"
            fi
            

        # Print the full command
        echo "Running command: $CMD"

        # Execute the Python command
        eval $CMD
    fi
done <<< "$TSTART_LIST"

