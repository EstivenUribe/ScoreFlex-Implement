#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Gunicorn
pip install gunicorn

# Install any other build steps here (if needed)
