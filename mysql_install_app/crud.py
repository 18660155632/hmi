from sqlalchemy.orm import Session
from sqlalchemy.sql import union
from . import models, schemas
from fastapi import HTTPException


def get_server(db: Session):
    return db.query(models.Server).all()

def get_server_by_host(db: Session, host: str):
    return db.query(models.Server).filter(models.Server.server_host == host).all()

def get_mysql_instance(db: Session):
    return db.query(models.Instance).all()

def get_mysql_instance_by_project(db: Session, project: str):
    return db.query(models.Instance).filter(models.Instance.mysql_project == project).all()

def get_mysql_instance_by_host(db: Session, host: str):
    return db.query(models.Instance).filter(models.Instance.mysql_host == host).all()

def get_mysql_instance_by_host_port(db: Session, host: str, port: str):
    return db.query(models.Instance).filter(models.Instance.mysql_host == host, models.Instance.mysql_port == port).all()

def get_mysql_instance_log(db: Session):
    return db.query(models.Log).all()

def get_mysql_instance_log_by_host(db: Session, host: str):
    return db.query(models.Log).filter(models.Log.host == host).all()

def get_mysql_instance_log_by_host_port(db: Session, host: str, port: str):
    return db.query(models.Log).filter(models.Log.host == host, models.Log.port == port).all()

def get_ms(db: Session):
    return db.query(models.MS).all()

def get_ms_by_host(db: Session, host: str):
    list1 = db.query(models.MS).filter(models.MS.master_host == host).all()
    list2 = db.query(models.MS).filter(models.MS.slave_host == host).all()
    return list1 + list2

def get_ms_by_host_port(db: Session, host: str, port: str):
    list1 = db.query(models.MS).filter(models.MS.master_host == host, models.MS.master_port == port).all()
    list2 = db.query(models.MS).filter(models.MS.slave_host == host, models.MS.slave_port == port).all()
    return list1 + list2

def get_ms_by_mhost_mport(db: Session, host: str, port: str):
    list1 = db.query(models.MS).filter(models.MS.master_host == host, models.MS.master_port == port).all()
    return list1

def get_user_by_host_port(db: Session, host: str, port: str):
    return db.query(models.User).filter(models.User.server_host == host, models.User.server_port == port).all()

def get_user_by_host_port_user(db: Session, host: str, port: str, user: str):
    return db.query(models.User).filter(models.User.server_host == host, models.User.server_port == port, models.User.client_user == user).all()

def get_user_by_host_port_chost(db: Session, host: str, port: str, chost: str):
    return db.query(models.User).filter(models.User.server_host == host, models.User.server_port == port, models.User.client_host == chost, ).all()

def get_user_by_host_port_user_chost(db: Session, host: str, port: str, user: str, chost: str):
    return db.query(models.User).filter(models.User.server_host == host, models.User.server_port == port, models.User.client_user == user, models.User.client_host == chost).all()


#添加server信息
def add_server(db: Session, server: dict):
    db_server = models.Server(
        server_host=server["server_host"],
        server_password=server["server_password"], 
        server_type=server["server_type"], 
        server_role=server["server_role"], 
        server_mark=server["server_mark"],
        disk_part=server["disk_part"],
        lv_manage=server["lv_manage"],
        vg_name=server["vg_name"]
    )
    try:
        db.add(db_server)
        db.commit()
        db.refresh(db_server)
        return True
    except:
        return False


#添加mysql实例信息
def add_mysql_instance(db: Session, instance: dict):
    db_instance = models.Instance(
        mysql_project=instance["mysql_project"],
        mysql_version=instance["mysql_version"],
        mysql_host=instance["mysql_host"],
        mysql_port=instance["mysql_port"],
        mysql_password=instance["mysql_password"],
        mysql_role=instance["mysql_role"],
        mysql_mark=instance["mysql_mark"],
        disk_usage_gb=instance["disk_usage_gb"],
        innodb_buffer_pool_size=instance["innodb_buffer_pool_size"]
    )
    try:
        db.add(db_instance)
        db.commit()
        db.refresh(db_instance)
        return True
    except:
        return False


#添加实例操作日志信息
def add_log(db: Session, log: dict):
    db_log = models.Log(
        host=log['host'], 
        port=log['port'], 
        action=log['action'], 
        action_result=log['action_result']
    )
    try:
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return True
    except:
        return False


#添加主从关系信息
def add_ms(db: Session, ms: dict):
    db_ms = models.MS(
        master_host=ms['master_host'], 
        master_port=ms['master_port'], 
        slave_host=ms['slave_host'], 
        slave_port=ms['slave_port'], 
        repl_type=ms['repl_type']
    )
    try:
        db.add(db_ms)
        db.commit()
        db.refresh(db_ms)
        return True
    except:
        return False


#添加用户授权信息
def add_user(db: Session, user: dict):
    db_user = models.User(
        server_host=user['server_host'], 
        server_port=user['server_port'], 
        db_tb=user['db_tb'],
        client_user=user['client_user'],
        client_host=user['client_host'],
        client_pass=user['client_pass'],
        user_role=user['user_role'],
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return True
    except:
        return False


#删除server信息
def del_server(db: Session, host: str):
    try:
        db.query(models.Server).filter(models.Server.server_host == host).delete()
        db.commit()
        return True
    except:
        return False
    


#删除mysql实例信息
def del_mysql_instance(db: Session, host: str, port: str):
    try:
        db.query(models.Instance).filter(models.Instance.mysql_host == host, models.Instance.mysql_port == port).delete()
        db.commit()
        return True
    except:
        return False


#删除mysql实例信息
def del_mysql_instance_by_host(db: Session, host: str):
    try:
        db.query(models.Instance).filter(models.Instance.mysql_host == host).delete()
        db.commit()
        return True
    except:
        return False


#删除主从信息
def del_ms(db: Session, host: str, port: str):
    try:
        db.query(models.MS).filter(models.MS.master_host == host, models.MS.master_port == port).delete()
        db.query(models.MS).filter(models.MS.slave_host == host, models.MS.slave_port == port).delete()
        db.commit()
        return True
    except:
        return False


#删除主从信息
def del_ms_by_host(db: Session, host: str):
    try:
        db.query(models.MS).filter(models.MS.master_host == host).delete()
        db.query(models.MS).filter(models.MS.slave_host == host).delete()
        db.commit()
        return True
    except:
        return False


#删除用户授权信息
def del_user(db: Session, host: str, port: str, user: str, chost: str):
    try:
        db.query(models.User).filter(models.User.server_host == host, models.User.server_port == port, models.User.client_user == user, models.User.client_host == chost).delete()
        db.commit()
        return True
    except:
        return False


#删除用户授权信息
def del_user_by_host_port(db: Session, host: str,  port: str):
    try:
        db.query(models.User).filter(models.User.server_host == host, models.User.server_port == port).delete()
        db.commit()
        return True
    except:
        return False


#删除用户授权信息
def del_user_by_host(db: Session, host: str):
    try:
        db.query(models.User).filter(models.User.server_host == host).delete()
        db.commit()
        return True
    except:
        return False


#修改server的状态信息
def change_server_ststus(db: Session, host: str, status: str):
    try:
        db.query(models.Server).filter(models.Server.server_host == host).update({"server_status":status})
        db.commit()
        return True
    except:
        raise False


#更新server资源信息
def update_server_info(
    db: Session, host: str, 
    memory_all: str, 
    memory_free: str, 
    disk_all: str, 
    disk_free: str
):
    try:
        db.query(models.Server).filter(models.Server.server_host == host).update({
            "memory_all":memory_all, 
            "memory_free":memory_free, 
            "disk_all":disk_all, 
            "disk_free":disk_free
        })
        db.commit()
        return True
    except:
        return False

