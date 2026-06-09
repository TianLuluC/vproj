#!/bin/bash
# 参数定义
CAMERA_ID=$1

CAMERA_STATUS=$( ps -ef | grep $CAMERA_ID | grep -v grep | grep python3 | awk '{print $2}')
echo "当前摄像头状态：${CAMERA_STATUS}"
if [ -n "$CAMERA_STATUS" ]; then
  echo "停止label-${CAMERA_ID}"
  kill -9 $CAMERA_STATUS
fi






