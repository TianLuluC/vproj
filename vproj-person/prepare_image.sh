#!/bin/bash

# 确保当前镜像为最新镜像
IMAGE_IDS=$(docker images --filter "reference=personnel_image_unique*" -q)

if [ -n "$IMAGE_IDS" ];then
    echo "$IMAGE_IDS" | xargs docker rmi -f
    echo "Image has removed, now rebuild"
else
    echo "No image, now build"
fi

# 创建镜像
BUILDKIT_PROGRESS=tty docker build -t personnel_image_unique:latest -f docker/x86_64.dockerfile ./docker

if [ $? -eq 0 ]; then
    echo "👍 good: Image build succeeded!"
else
    echo "❌ Error: Image build failed!"
    exit 1
fi