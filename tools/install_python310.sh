#!/bin/bash
set -e

echo '=== 安装 Python 3.10 ==='

# 检查是否已安装
if command -v python3.10 &> /dev/null; then
    echo 'Python 3.10 已安装:'
    python3.10 --version
    exit 0
fi

# 安装依赖
echo '[1/4] 安装编译依赖...'
yum groupinstall -y "Development Tools" || true
yum install -y openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel xz-devel wget

# 下载 Python 3.10.13 源码
echo '[2/4] 下载 Python 3.10.13 源码...'
cd /tmp
if [ ! -f Python-3.10.13.tgz ]; then
    wget https://www.python.org/ftp/python/3.10.13/Python-3.10.13.tgz
fi

# 解压
echo '[3/4] 解压并编译（这可能需要几分钟）...'
tar -xzf Python-3.10.13.tgz
cd Python-3.10.13

# 配置、编译、安装
./configure --prefix=/usr/local --enable-optimizations --with-ssl-default-suites=openssl
make -j4
make altinstall

# 创建符号链接
echo '[4/4] 创建符号链接...'
ln -sf /usr/local/bin/python3.10 /usr/bin/python3.10 2>/dev/null || true
ln -sf /usr/local/bin/pip3.10 /usr/bin/pip3.10 2>/dev/null || true

# 验证安装
echo ''
echo '=== 安装完成 ==='
/usr/local/bin/python3.10 --version
/usr/local/bin/pip3.10 --version

echo ''
echo 'Python 3.10 安装位置: /usr/local/bin/python3.10'

