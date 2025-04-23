#!/bin/bash
# mjpg-streamer + PageKite startup script

RESOLUTION="640x480"
FPS="10"
PORT="8080"
PAGEKITE_HOST="beesscamera.pagekite.me"   
PAGEKITE_SERVICE="8080"               
 


echo "Starting mjpg-streamer on port $PORT at $RESOLUTION $FPS FPS..."
mjpg_streamer -i "input_uvc.so -r $RESOLUTION -f $FPS" \
             -o "output_http.so -w /usr/local/share/mjpg-streamer/www -p $PORT" &


sleep 2

echo "Starting PageKite tunneling $PAGEKITE_HOST to local port $PAGEKITE_SERVICE..."
#
pagekite.py $PAGEKITE_SERVICE $PAGEKITE_HOST &

echo "MJPG-streamer and PageKite are now running in the background."



