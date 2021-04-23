from sqlalchemy import Boolean, Column, Integer, String, DateTime, func, UniqueConstraint
from .database import Base


#创建server模型
class Server(Base):
    #基础信息
    __tablename__ = "mysql_servers"
    sid = Column(Integer, primary_key=True)                                 #自增主键
    server_host = Column(String(20), nullable=False, unique=True)           #机器ip地址
    server_password = Column(String(100), nullable=False)                   #linux密码
    server_type = Column(String(10), nullable=False)                        #区分物理机和虚拟机
    server_role = Column(String(10), nullable=False)                        #区分主库机器还是从库机器
    server_status = Column(String(10), nullable=False, server_default="0")  #0：未传输文件、未初始化  1：文件已传输、已初始化
    server_mark = Column(String(100))                                       #备注信息
    disk_part = Column(String(10), nullable=False, server_default="/data")  #安装数据库的磁盘分区
    lv_manage = Column(String(10), nullable=False, server_default="no")     #是否为部署的每个MySQL实例分配一个lv分区
    vg_name = Column(String(10), nullable=False, server_default="datavg")   #卷组名，lv_manage为yes才有用
    #资源信息（GB）
    memory_all = Column(Integer)
    memory_free = Column(Integer)
    disk_all = Column(Integer)
    disk_free = Column(Integer)


#创建mysql实例模型
class Instance(Base):
    __tablename__ = "mysql_instances"
    mid = Column(Integer, primary_key=True)                             #自增主键
    mysql_project = Column(String(10), nullable=False)                  #mysql实例项目名
    mysql_version = Column(String(10), nullable=False)                  #mysql版本号
    mysql_host = Column(String(20), nullable=False)                     #mysql实例地址
    mysql_port = Column(String(10), nullable=False)                     #mysql实例端口号
    mysql_password = Column(String(100), nullable=False)                #mysql本地root密码
    mysql_role = Column(String(10), nullable=False)                     #mysql角色：master，slave
    mysql_install_time = Column(DateTime, nullable=False, server_default=func.now())      #安装时间
    mysql_mark = Column(String(100))                                    #备注信息
    disk_usage_gb = Column(Integer, nullable=False)                     #预计磁盘使用量
    innodb_buffer_pool_size = Column(String(20), nullable=False)        #自定义buffer_pool大小
    
    __table_args__ = (
        UniqueConstraint("mysql_host", "mysql_port", name="uniq_host_port"),
    )


#创建mysql实例处理日志模型
class Log(Base):
    __tablename__ = "mysql_instance_logs"
    lid = Column(Integer, primary_key=True)                             #自增主键
    host = Column(String(20), nullable=False, index=True)
    port = Column(String(10), nullable=False, index=True)
    action = Column(String(10), nullable=False)                         #操作：install、remove
    action_time = Column(DateTime, nullable=False, server_default=func.now())   #操作时间
    action_result = Column(Boolean, nullable=False)                     #操作结果


#主从关系表
class MS(Base):
    __tablename__ = "master_slave_relation"
    id = Column(Integer, primary_key=True)                              #自增主键
    master_host = Column(String(20), nullable=False)                    #主库地址
    master_port = Column(String(10), nullable=False)                    #主库端口
    slave_host = Column(String(20), nullable=False)                     #从库地址
    slave_port = Column(String(10), nullable=False)                     #从库端口
    repl_type = Column(String(10), nullable=False)                      #主从复制类型
    start_time = Column(DateTime, nullable=False, server_default=func.now())   #搭建时间


#用户授权信息表
class User(Base):
    __tablename__ = "mysql_user_privileges"
    uid = Column(Integer, primary_key=True)                                    #自增主键
    server_host = Column(String(20), nullable=False, index=True)               #数据库地址
    server_port = Column(String(10), nullable=False, index=True)               #数据库端口
    db_tb = Column(String(10), nullable=False)                                 #授权库.授权表
    client_user = Column(String(20), nullable=False)                           #被授权用户名
    client_host = Column(String(20), nullable=False)                           #被授权客户端地址
    client_pass = Column(String(100), nullable=False)                           #被授权用户密码
    user_role = Column(String(10), nullable=False)                             #用户权限（readonly、readwrite）
    grant_time = Column(DateTime, nullable=False, server_default=func.now())   #授权时间