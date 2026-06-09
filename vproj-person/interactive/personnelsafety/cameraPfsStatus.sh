#!/bin/bash

CAMERA_ID=$1
CAMERA_STATUS=$( ps -ef | grep ${CAMERA_ID} | grep -v grep | grep python3 | awk '{print $2}' | xargs echo )
if [ -n "$CAMERA_STATUS" ];then
  echo "$CAMERA_STATUS"
else
  echo "failed"
fi
