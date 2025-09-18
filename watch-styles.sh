#!/bin/bash

# This script builds the Tailwind CSS styles for the project.
# Ensure the script exits on error
set -e

# Build the Tailwind CSS styles
npx @tailwindcss/cli -i ./vsm_app/static/css/input.css -o ./vsm_app/static/css/output.css --watch
# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Tailwind CSS styles built successfully."
else
    echo "Failed to build Tailwind CSS styles."
    exit 1
fi
