# HMI
MySQL数据库部署及管理平台
  
  
  
### 功能：  
  1. 宿主机管理：包括向宿主机传输文件、调优宿主机参数以适配MySQL  
  2. 部署MySQL实例：支持5.6、5.7、8.0版本的MySQL部署，支持单机多版本多实例  
  3. 主从搭建：支持5.6、5.7、8.0版本的MySQL搭建异步、半同步主从。（5.6版本因其半同步复制不完善，所以仅支持异步主从）  
  4. 用户授权：支持授权用户（只读、读写）、删除用户、用户权限查看。  
  
### 2.0版本新增功能：
  1. 支持lvm管理，每个实例目录一个lv
  2. 支持innodb_buffer_pool_size调整为MB或者GB级别
  3. 服务器和数据库实例root密码加密（授权的用户密码未加密，为了以后容易查找）

### 环境要求：
  - centos7
  - python3.7.2
  - mysql8.0.22

### 平台搭建：
  #### 安装mysql数据库
  首先通过mysql_install.sh脚本安装本系统的数据库，具体细节略  
  #### 安装python3及部分依赖
  yum install wget gcc make libffi-devel zlib-devel openssl openssl-devel xz sshpass git -y  
  wget "https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tar.xz"   
  tar -xvf Python-3.7.2.tar.xz   
  cd Python-3.7.2   
  ./configure prefix=/usr/local/python3   
  make && make install   
  ln -fs /usr/local/python3/bin/python3 /usr/bin/python3   
  ln -fs /usr/local/python3/bin/pip3 /usr/bin/pip3   
  pip3 install --upgrade pip
  #### git克隆
  cd /opt  
  git clone -b dev https://github.com.cnpmjs.org/369070203/HMI.git  
  #### 传入MySQL安装包
  自行下载MySQL各个版本免编译安装包放入/opt/HMI/mysql_install_files/
  #### 启动应用
  bash /opt/HMI/start.sh
  
  
### 注意事项：
  1. 程序需要放在/opt/目录下，因为传输文件对这个路径有依赖。
  2. 每个宿主机只能安装MySQL一个大版本里的其中一个小版本，比如8.0版本可以只安装8.0.22，如果里边还有8.0.21版本的软件包，  
     否则删除实例时会有bug（要删除的实例关不掉，因为关闭实例时使用的mysqladmin命令是通过/opt/mysql/mysql-8.0.*/bin/mysqladmin这种方式使用的）。
# HMI
