#!/bin/bash

echo "创建容器"
IMAGE_ID=$(docker images --filter \
          "reference=personnel_image_unique*" -q | head -n 1)
CONTAINER_ID=$(docker ps -a --filter "name=personnel_unique" -q)

# Mount的绝对路径
# PROJECT_HOST_PATH=$(cd "$(dirname "$0")"/.. && pwd) # 该文件所在目录的上级目录
# PROJECT_HOST_PATH=$(find /home -maxdepth 3 -type d -name "zxauto-vproj" | head -n 1)
PROJECT_HOST_PATH="/home/yinxing2xmc/zxauto/zxauto-vproj/personnel_safety_project"
# 若容器不存在，则通过image创建
if [ -n "$CONTAINER_ID" ];then
    echo "Container has existed!"
else
    echo "Container hasn't existed!"

    # 动态获取宿主机的第一个 IP 地址
    HOST_IP=$(hostname -I | awk '{print $1}')
    echo "Detected Host IP: $HOST_IP"

    docker run -d --name personnel_unique --gpus all \
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


if [ -f "$PROJECT_HOST_PATH/nohup.out" ]; then
    rm -f "$PROJECT_HOST_PATH/nohup.out"
    rm -f "$PROJECT_HOST_PATH/log"
    echo "Old nohup.out removed from host."
fi

echo "容器重启"
docker restart $CONTAINER_ID
sleep 5s