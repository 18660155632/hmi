FROM 172.16.2.213/base_images/python37:v1.1
RUN yum install wget gcc make libffi-devel zlib-devel openssl openssl-devel xz sshpass git -y
RUN pip3.7 install -i https://mirrors.aliyun.com/pypi/simple --upgrade pip && \
    pip3.7 install -i https://mirrors.aliyun.com/pypi/simple uvicorn fastapi sqlalchemy pymysql pyDes cryptography &&\
    mkdir -p /opt/HMI/mysql_install_app
WORKDIR /opt/HMI/
COPY  mysql_install_app ./mysql_install_app/
WORKDIR /opt/HMI/

