#!/bin/bash

SCRIPT_DIR="$(dirname "$0")"

# Define the path to your virtual environment (adjust as needed)
VENV_DIR="$SCRIPT_DIR/venv"

# Define the path to your Python script (adjust as needed)
PYTHON_SCRIPT="$SCRIPT_DIR/src/main.py"
PYTHON_ARGS="--level debug --verbose false --interactive false"

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

# Check if the virtual environment was activated successfully
if [ $? -eq 0 ]; then
  # Run the Python script
  nohup python "$PYTHON_SCRIPT" $PYTHON_ARGS > /dev/null 2>&1 &
  pid=$!
  disown $pid
  echo $pid > "$SCRIPT_DIR/main.pid"
else
  echo "Error: Failed to activate virtual environment."
  exit 1 # Exit with error code
fi

# optional error handling for the python script itself.
if [ $? -ne 0 ]; then
  echo "Error: Python script failed."
  exit 1
fi

exit 0 # Exit with success codes
