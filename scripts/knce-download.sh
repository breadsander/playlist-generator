#!/bin/bash

# Stream URL
STREAM_URL="https://shoutcast.brownrice.com:8002/stream"

# Output file
OUTPUT_DIR="/home/wellings/webradio/knce-recordings"
mkdir -p $OUTPUT_DIR
TIMESTAMP=$(date +"%Y-%m-%d")
OUTPUT_FILE="$OUTPUT_DIR/knce_$TIMESTAMP.mp3"

# Record the stream
ffmpeg -i $STREAM_URL -t 7320 -c copy $OUTPUT_FILE
