FROM python:3.11.7-slim

WORKDIR /app

COPY /requirements.txt .
COPY /local_packages/ ./local_packages/
RUN pip3 install -r requirements.txt --no-cache-dir \
    -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用国内源且不修改hosts文件
RUN echo "deb http://mirrors.aliyun.com/debian/ bookworm main non-free contrib" > /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian/ bookworm main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian-security/ bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian/ bookworm-updates main non-free contrib" >> /etc/apt/sources.list && \
    # 强制IPv4
    echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 && \
    # 备份原始sources.list以防被修改
    cp /etc/apt/sources.list /etc/apt/sources.list.bak && \
    # 更新并安装基础工具
    apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg2 && \
    # 使用清华NodeSource镜像并阻止其修改源
    curl -fsSL https://mirrors.tuna.tsinghua.edu.cn/nodesource/deb/setup_18.x | sed -e 's|deb.debian.org|mirrors.aliyun.com|g' -e 's|security.debian.org|mirrors.aliyun.com/debian-security|g' | bash - && \
    # 恢复被可能修改的源配置
    cp /etc/apt/sources.list.bak /etc/apt/sources.list && \
    # 安装Node.js
    apt-get install -y --no-install-recommends nodejs npm && \
    # 清理缓存
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /etc/apt/sources.list.bak


COPY app/ .

# EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
