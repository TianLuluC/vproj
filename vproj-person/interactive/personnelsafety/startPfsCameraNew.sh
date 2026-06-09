#!/bin/bash

echo "创建容器"
IMAGE_ID=$(docker images --filter \
          "reference=personnel_image_unique*" -q | head -n 1)
CONTAINER_ID=$(docker ps -a --filter "name=personnel_unique" -q)

# Mount的绝对路径
# PROJECT_HOST_PATH=$(cd "$(dirname "$0")"/.. && pwd) # 该文件所在目录的上级目录
# PROJECT_HOST_PATH=$(find /home -maxdepth 3 -type d -name "zxauto-vproj" | head -n 1)
PROJECT_HOST_PATH="/home/yinxing2xmc/zxauto/zxauto-vproj/personnel_safety_project"
# PROJECT_HOST_PATH="/home/yinxing2xmc/zxauto/zxauto-vproj"
echo "lujing:  $PROJECT_HOST_PATH"
# 若容器不存在，则通过image创建
if [ -n "$CONTAINER_ID" ];then
    echo "Container has existed!"
else
    echo "Container not existed!"

    # 动态获取宿主机的第一个 IP 地址
    HOST_IP=$(hostname -I | awk '{print $1}')
    echo "Detected Host IP: $HOST_IP"

    docker run -itd --name personnel_unique --gpus all \
               --ipc host --network host --privileged \
               -e HOST_IP="$HOST_IP" \
               -v "$PROJECT_HOST_PATH":/home/workspace \
               -w /home/workspace "$IMAGE_ID"

    if [ $? -ne 0 ]; then
        echo "$(date) - Failed to creat container. "
        exit 1
    fi
    CONTAINER_ID=$(docker ps -a --filter "name=personnel_unique" -q)  
    echo "Container Created. ID:$CONTAINER_ID !"
fi

echo "====================  配置摄像头参数 ===================="
# 如果脚本运行没有传参，则使用默认的硬编码参数
cameraAddress=${1:-"rtsp://admin:hik12345@10.32.132.20:554/h264/ch1/main/av_stream"}
cameraId=${2:-"1314"}
cameraLocation=${3:-"12"}
alarmFrequency=${4:-"5"} # 给一个默认值5，防止为空

echo "摄像头地址：$cameraAddress 摄像头id: $cameraId 摄像头位置：$cameraLocation 报警间隔：$alarmFrequency"

docker start $CONTAINER_ID

cameraStatus=$(ps -ef | grep $cameraId | grep -v grep | \
                        grep python3 | awk '{print $2}')

echo "当前摄像头状态：$cameraStatus"
if [ -n "$cameraStatus" ];then
    echo "$cameraStatus"
    kill -9 $cameraStatus
fi

# 启动
RUN_ARGS="$cameraAddress $cameraId $cameraLocation $alarmFrequency"
echo "脚本启动参数：$RUN_ARGS"

docker exec -d "$CONTAINER_ID" sh -c "nohup python3 main.py $RUN_ARGS >/dev/null 2>log &"
echo "Start success!"




