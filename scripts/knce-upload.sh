#!/bin/bash

# Directory to upload
UPLOAD_DIR="/home/wellings/webradio/knce-recordings"

# Rclone remote and path
REMOTE="knce-recordings:"

# Upload files
rclone move $UPLOAD_DIR $REMOTE --verbose
