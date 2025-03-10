#!/bin/bash

# Set up signal handling for graceful shutdown
trap 'echo "Received signal, exiting."; exit 0' SIGTERM SIGINT

# Run Gunicorn and log output to a file for debugging
gunicorn -w 4 -b 0.0.0.0:5000 app:app 2>&1 > gunicorn.log

# Check if Gunicorn failed
if [ $? -ne 0 ]; then
  echo "Gunicorn failed. Starting shell for debugging."
  bash
fi
