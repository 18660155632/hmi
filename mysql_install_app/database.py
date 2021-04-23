import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

#SQLALCHEMY_DATABASE_URL = "mysql+pymysql://hmiadmin:123456@172.16.1.25:3306/hmi?charset=utf8mb4"
hmi_host = os.popen('echo ${hmi_host}').read().replace('\n', '')
hmi_port = os.popen('echo ${hmi_port}').read().replace('\n', '')
hmi_user = os.popen('echo ${hmi_user}').read().replace('\n', '')
hmi_password = os.popen('echo ${hmi_password}').read().replace('\n', '')
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://"+hmi_user+":"+hmi_password+"@"+hmi_host+":"+hmi_port+"/hmi?charset=utf8mb4"

#创建SQLAlchemy引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True
)

#创建数据库会话类
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#创建数据库基础模型
Base = declarative_base()
