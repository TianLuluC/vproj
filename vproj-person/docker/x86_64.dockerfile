ARG TAG=24.01-py3

FROM nvcr.io/nvidia/tensorrt:${TAG} AS tensorrtx

ENV DEBIAN_FRONTEND=noninteractive

# basic tools
RUN apt update && apt-get install -y --fix-missing --no-install-recommends \
sudo wget curl git ca-certificates ninja-build tzdata pkg-config \
gdb libglib2.0-dev libmount-dev locales \
&& rm -rf /var/lib/apt/lists/*

RUN  pip3 uninstall -y numpy \
&& pip3 install --no-cache-dir -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple \
yapf isort cmake-format pre-commit opencv-python==4.8.1.78 numpy==1.23.5 \
requests nvidia-ml-py3 ffmpeg-python 

## fix a potential pre-commit error
RUN locale-gen "en_US.UTF-8"

## override older cmake
RUN find /usr/local/share -type d -name "cmake-*" -exec rm -rf {} +
COPY ./pkg/cmake-3.30.0-linux-x86_64.sh /tmp/cmake.sh
RUN bash /tmp/cmake.sh --skip-license --exclude-subdir --prefix=/usr/local \   
&& rm -f /tmp/cmake.sh

RUN apt update && apt install -y ffmpeg \
&& apt-get update && apt-get install -y libopencv-dev \
&& rm -rf /var/lib/apt/lists/*

# # a template to build opencv and opencv_contrib from source
# COPY opencv /workspace/opencv
# COPY opencv_contrib /workspace/opencv_contrib

# RUN cmake -S /workspace/opencv -B /workspace/opencv/build -G Ninja \
#     -DBUILD_LIST=core,calib3d,imgproc,imgcodecs,highgui \
#     -DOPENCV_EXTRA_MODULES_PATH="/workspace/opencv_contrib/modules" \
#     -DCMAKE_BUILD_TYPE=RELEASE \
#     -DCMAKE_INSTALL_PREFIX=/usr/local \
#     -DENABLE_FAST_MATH=ON \
#     -DOPENCV_GENERATE_PKGCONFIG=ON \
#     \
#     # ==================== Python3 绑定配置 ====================
#     -DBUILD_opencv_python2=OFF \
#     -DBUILD_opencv_python3=ON \
#     -DPYTHON3_EXECUTABLE=$(which python3) \
#     -DPYTHON3_INCLUDE_DIR=$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
#     -DPYTHON3_LIBRARY=$(python3 -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))") \
#     -DPYTHON3_NUMPY_INCLUDE_DIRS=$(python3 -c "import numpy; print(numpy.get_include())") \
#     \
#     -DBUILD_JAVA=OFF \
#     -DBUILD_DOCS=OFF \
#     -DBUILD_PERF_TESTS=OFF \
#     -DBUILD_TESTS=OFF \
#     \
#     && ninja -C /workspace/opencv/build -j$(nproc) install \
#     && ldconfig \
#     && rm -rf /workspace/opencv /workspace/opencv_contrib /workspace/opencv/build

# RUN git clone -b 4.13.0 https://github.com/opencv/opencv_contrib.git \
# && git clone -b 4.13.0 https://github.com/opencv/opencv.git opencv \
# && cmake -S opencv -B opencv/build -G Ninja \
# -DBUILD_LIST=core,calib3d,imgproc,imgcodecs,highgui \
# -DOPENCV_EXTRA_MODULES_PATH="/workspace/opencv_contrib/modules" \
# -DCMAKE_BUILD_TYPE=RELEASE \
# -DCMAKE_INSTALL_PREFIX=/usr/local \
# -DENABLE_FAST_MATH=ON \
# -DOPENCV_GENERATE_PKGCONFIG=ON \
# -DBUILD_opencv_python2=OFF \
# -DBUILD_opencv_python3=on \
# -DBUILD_JAVA=OFF \
# -DBUILD_DOCS=OFF \
# -DBUILD_PERF_TESTS=OFF \
# -DBUILD_TESTS=OFF \
# && ninja -C opencv/build install
