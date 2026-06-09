#!/bin/bash
echo "*********************人员安全区域绘制坐标保存**********"
PersonnelSafety=$1
echo "id: $PersonnelSafety"

CONTAINER_ID=$(docker ps -a --filter "name=personnel_unique" -q)  
echo "接收所有参数：$@"
echo "id: $PersonnelSafety"

docker start $CONTAINER_ID
# 启动
docker exec -itd ${CONTAINER_ID} nohup python3 modules/regoin.py $@ >/dev/null 2>log &
echo "启动成功！"

