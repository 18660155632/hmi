from typing import List, Optional, Set
from fastapi import Query, Form
from pydantic import BaseModel
import datetime

#创建Pydantic模型（Pydantic模型在读取数据以及从API返回数据时将使用）
#Optional[]使得对应参数返回时允许为空，不加会报错

class ServerBase(BaseModel):
    server_host: str = "172.16.1.xx"
    server_password: str = "123456"
    server_type: str = "physical"
    server_role: str = "master"
    server_mark: Optional[str] = "无"
    disk_part: str = "/data"
    lv_manage: str = "no"
    vg_name: str = "datavg"

class Server(ServerBase):
    sid: int
    server_status: str
    memory_all: Optional[int]
    memory_free: Optional[int]
    disk_all: Optional[int]
    disk_free: Optional[int]

    class Config:
        orm_mode = True


class ServerShow(BaseModel):
    server_host: str
    server_type: str
    server_role: str
    server_mark: Optional[str]
    disk_part: str
    server_status: str
    lv_manage: str
    vg_name: str
    memory_all: Optional[int]
    memory_free: Optional[int]
    disk_all: Optional[int]
    disk_free: Optional[int]
    
    class Config:
        orm_mode = True

class InstanceBase(BaseModel):
    mysql_project: str = "test"
    mysql_version: str = "x.x"
    mysql_host: str = "172.16.1.xx"
    mysql_port: str = "3306"
    mysql_password: str = "123456"
    #mysql_role: str = "master"
    mysql_mark: Optional[str] = "无"
    disk_usage_gb: int = 20
    innodb_buffer_pool_size: str = "1G"


class Instance(InstanceBase):
    mid: int
    mysql_install_time: datetime.datetime

    class Config:
        orm_mode = True


class InstanceShow(BaseModel):
    mysql_project: str = "test"
    mysql_version: str = "x.x"
    mysql_host: str = "172.16.1.xx"
    mysql_port: str = "3306"
    mysql_role: str = "master"
    mysql_mark: Optional[str] = "无"
    innodb_buffer_pool_size: str = "1G"
    mysql_install_time: datetime.datetime

    class Config:
        orm_mode = True


class ActionLog(BaseModel):
    lid: int
    host: str
    port: str
    action: str
    action_time: datetime.datetime
    action_result: bool

    class Config:
        orm_mode = True


class MS(BaseModel):
    master_host: str
    master_port: str
    slave_host: str
    slave_port: str
    repl_type: str
    start_time: datetime.datetime

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    db_tb: str
    client_user: str
    client_host: str
    user_role: str
    grant_time: datetime.datetime

    class Config:
        orm_mode = True

class User(UserBase):
    server_host: str
    server_port: str
    client_pass: str

    class Config:
        orm_mode = True