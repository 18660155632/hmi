from typing import List
from fastapi import Depends, FastAPI, HTTPException, Query, Form
from sqlalchemy.orm import Session
from . import crud, models, schemas, mima
from .database import SessionLocal, engine
import os
from enum import Enum, unique
import re
from .lv_manage import lv_create, lv_remove


#创建数据库表
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title = "HMI系统",
    description = "部署及管理MySQL数据库实例",
    version= " 2.0 ",
    #openapi_tag = tags_metadata,
    docs_url = "/docs",
    redoc_url = "/redoc"
)


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#机器类型枚举类
class ServerType(str, Enum):
    physical = "physical"
    virtual = "virtual"


#传输文件分类
class FileType(str, Enum):
    all_file = "all_file"
    sh = "sh"
    cnf = "cnf"
    tar = "tar"


#数据库版本号枚举类
class InstanceVersion(str, Enum):
    v6 = "5.6"
    v7 = "5.7"
    v8 = "8.0"


#数据库角色枚举类
class InstanceRole(str, Enum):
    master = "master"
    slave = "slave"


#数据库复制类型枚举类
class ReplType(str, Enum):
    async_type = "async"
    semi_sync_type = "semi_sync"


#数据库用户角色
class UserRole(str, Enum):
    readonly = "readonly"
    readwrite = "readwrite"


#实例是否单独用LV管理
class LvManage(str, Enum):
    yes = "yes"
    no = "no"


#获取server列表
@app.get("/get_server/", response_model= List[schemas.ServerShow], tags=["宿主机操作"], summary="获取server信息")
def get_servers(server_host: str = Query(None, alias="地址"), db: Session = Depends(get_db)):
    """
    查询方式：

    - 1、不传参：获取所有server信息
    - 2、传入host：获取单个server信息
    """
    if server_host is None:
        db_servers = crud.get_server(db)
    else:
        db_servers = crud.get_server_by_host(db, host=server_host)
    if db_servers:
        return db_servers
    else:
        raise HTTPException(status_code=404, detail="Server info not found")


#添加server信息
@app.post("/add_server/", tags=["宿主机操作"], summary="添加server信息")
def add_server(
    server_host: str = Query(..., example="172.16.3.xx", alias="地址"),
    server_password: str = Query(..., example="123456", alias="密码"),
    disk_part: str = Query(..., example="/data", alias="磁盘分区"),
    server_type: ServerType = Query(..., alias="机器类型"),
    server_role: InstanceRole = Query(..., alias="机器角色"),
    lv_manage: LvManage = Query(..., alias="LV实例"),
    vg_name: str = Query(..., example="datavg", alias="VG名称"),
    server_mark: str = Query(None, alias="备注"),
    db: Session = Depends(get_db)
):
    """
    调用说明：

    - 1、磁盘分区决定数据库实例部署的目录位置，必须是df命令能看到的一级目录，否则会无法获取磁盘信息
    - 2、机器角色决定宿主机上的实例，能不能被复制，能不能作为从库
    - 3、LV实例决定宿主机是否为每个MySQL实例数据目录都分一个LV
    - 4、VG名称要输入一个已存在的VG，本系统不会去创建VG
    - 5、本API所做的事情包括：配置免密登陆、传输宿主机所需文件（耗时稍长）、初始化宿主机
    """
    db_server = crud.get_server_by_host(db, host=server_host)
    if db_server:
        raise HTTPException(status_code=400, detail="This host already registered!")
    #配置ssh免密
    if not ssh_config(server_host=server_host, server_password=server_password):
        return {"result": "SSH config failed!"}
    #判断vg是否存在
    if lv_manage == "yes":
        cmd = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s vgs %s"%(server_host, vg_name)
        return_code = os.system(cmd)
        if return_code != 0:
            return {"result": "VG not exists!"}
    #添加server信息
    server = {
        "server_host":server_host,
        "server_password":mima.jiami(server_password),
        "server_type":server_type,
        "server_role":server_role,
        "server_mark":server_mark,
        "disk_part":disk_part,
        "lv_manage":lv_manage,
        "vg_name":vg_name
    }
    if crud.add_server(db=db, server=server):
        #传输文件
        if not transfer_files(db=db, server_host=server_host, file_type=None):
            return {"result": "Files transfer failed!"}
        #初始化宿主机
        if not init_server(db=db, server_host=server_host):
            return {"result": "Server init failed!"}
        return {"result": "Server add successfully"}
    else:
        return {"result": "Server add failed!"}


#删除server信息
@app.post("/del_server/", tags=["宿主机操作"], summary="删除server信息")
def del_server(server_host: str = Query(..., example="172.16.3.xx", alias="地址"), db: Session = Depends(get_db)):
    """
    调用说明：

    - 1、慎重执行
    - 2、后端会删除指定宿主机的所有信息，包括宿主机信息、数据库实例信息、数据库账号信息、主从信息
    """
    db_server = crud.get_server_by_host(db, host=server_host)
    if not db_server:
        raise HTTPException(status_code=404, detail="Server info not found!")
    else:
        if crud.del_server(db=db, host=server_host) \
        and crud.del_mysql_instance_by_host(db=db, host=server_host) \
        and crud.del_user_by_host(db=db, host=server_host) \
        and crud.del_ms_by_host(db=db, host=server_host):
            return {"result": "Server delete successfully"}
        else:
            return {"result": "Server delete failed!"}


#ssh免密
#@app.post("/ssh_config/", tags=["宿主机操作"], summary="配置ssh免密")
def ssh_config(
    server_host: str = Query(..., example="172.16.3.xx", alias="地址"), 
    server_password: str = Query(..., example="123456", alias="密码"), 
    db: Session = Depends(get_db),
):
    #检查本机是否已创建公钥，没有则创建
    cmd1 = "ls /root/.ssh/id_rsa.pub"
    return_code = os.system(cmd1)
    if return_code != 0:
        cmd2 = "ssh-keygen -P '' -f /root/.ssh/id_rsa"
        os.system(cmd2)
    #传输本机公钥给宿主机器
    cmd3 = "sshpass -p '%s' ssh-copy-id -i /root/.ssh/id_rsa.pub  -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s"%(server_password,server_host)
    return_code = os.system(cmd3)
    if return_code == 0:
        return True
    else:
        return False


#传输文件到宿主机
@app.post("/transfer_files/", tags=["宿主机操作"], summary="向server传输文件（脚本、软件包、配置文件）")
def transfer_files(
    server_host: str = Query(..., example="172.16.3.xx", alias="地址"), 
    file_type: FileType = Query(None, alias="文件类型"),
    db: Session = Depends(get_db)
):
    """
    调用说明：

    - 1、默认以scp的方式传输所有部署及管理数据库所需文件
    - 2、也可选择传输指定类型的文件到宿主机（包括MySQL二进制安装包、配置文件、脚本）
    """
    db_server = crud.get_server_by_host(db=db, host=server_host)
    if not db_server:
        return False
    host = db_server[0].server_host
    if file_type is None:
        cmd = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r /opt/HMI/mysql_install_files root@%s:/'%(host)
    elif file_type == 'all_file':
        cmd = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r /opt/HMI/mysql_install_files root@%s:/'%(host)
    elif file_type == 'sh':
        cmd = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r /opt/HMI/mysql_install_files/*.sh root@%s:/mysql_install_files/'%(host)
    elif file_type == 'cnf':
        cmd = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r /opt/HMI/mysql_install_files/*.cnf root@%s:/mysql_install_files/'%(host)
    elif file_type == 'tar':
        cmd = 'scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -r /opt/HMI/mysql_install_files/*.tar.* root@%s:/mysql_install_files/'%(host)
    else:
        return False
    return_code = os.system(cmd)
    if return_code == 0:
        return True
    else:
        return False



#宿主机初始化
#@app.post("/init_server/", tags=["宿主机操作"], summary="初始化server（调优一些系统参数以适配MySQL）")
def init_server(
    server_host: str = Query(..., example="172.16.3.xx", alias="地址"), 
    db: Session = Depends(get_db)
):
    db_server = crud.get_server_by_host(db=db, host=server_host)
    if not db_server:
        return False
    if db_server[0].server_status == "0":
        host = db_server[0].server_host
        cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s bash /mysql_install_files/server_init.sh'%(host)
        return_code = os.system(cmd)
        if return_code == 0 and crud.change_server_ststus(db=db, host=host, status="1"):
            return True
        else:
            return False
    else:
        return True


#获取并更新服务器资源信息
#@app.post("/update_server/", tags=["宿主机操作"], summary="更新宿主机资源信息（内存、磁盘）")
def update_server(
    server_host: str = Query(..., example="172.16.3.xx", alias="地址"), 
    db: Session = Depends(get_db)
):
    db_server = crud.get_server_by_host(db=db, host=server_host)
    if db_server:
        vg_name = db_server[0].vg_name
        disk_part = db_server[0].disk_part
        cmd_mem = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s free -g | awk '/^Mem/{print $2,$7}'"%(server_host)
        if db_server[0].lv_manage == 'yes':
            cmd_disk = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s vgs --unit g | grep %s | awk '{print $6,$7}' | awk -F'[ .g]' '{print $1,$4}'"%(server_host, vg_name)
        elif db_server[0].lv_manage == 'no':
            cmd_disk = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s df -B 1g | grep %s$ | awk '{print $2,$4}'"%(server_host, disk_part)
        result_mem = os.popen(cmd_mem).readline().split()
        result_disk = os.popen(cmd_disk).readline().split()
        #print(result_mem)
        #print(result_disk)
        if result_mem and result_disk:
            memory_all = result_mem[0]
            memory_free = result_mem[1]
            disk_all = result_disk[0]
            disk_free = result_disk[1]
            if crud.update_server_info(
                db=db, host=server_host, 
                memory_all=memory_all, 
                memory_free=memory_free, 
                disk_all=disk_all, 
                disk_free=disk_free
            ):
                return True
            else:
                return False
        else:
            return False
    else:
        False


#查询mysql实例信息
@app.get("/get_mysql_instance/", response_model=List[schemas.InstanceShow], tags=["数据库操作"], summary="获取mysql实例信息")
def get_mysql_instance(
    mysql_host: str = Query(None, alias="地址"),
    mysql_port: str = Query(None, alias="端口"),
    mysql_project: str = Query(None, alias="项目名"),
    db: Session = Depends(get_db)
):
    """
    查询方式：

    - 1、不传参
    - 2、传入host
    - 3、传入host和port
    - 4、传入项目名
    """
    if mysql_host is None and mysql_port is None and mysql_project is None:
        db_instances = crud.get_mysql_instance(db)
    elif mysql_host is not None and mysql_port is None and mysql_project is None:
        db_instances = crud.get_mysql_instance_by_host(db, host=mysql_host)
    elif mysql_host is not None and mysql_port is not None and mysql_project is None:
        db_instances = crud.get_mysql_instance_by_host_port(db, host=mysql_host, port=mysql_port)
    elif mysql_host is None and mysql_port is None and mysql_project is not None:
        db_instances = crud.get_mysql_instance_by_project(db, project=mysql_project)
    else:
        raise HTTPException(status_code=400, detail="Please pass in the correct parameters!")
    if db_instances:
        return db_instances
    else:
        raise HTTPException(status_code=404, detail="MySQL instance info not found!")


#查询mysql实例操作日志信息
@app.get("/get_mysql_instance_log/", response_model=List[schemas.ActionLog], tags=["数据库操作"], summary="获取mysql实例操作日志")
def get_mysql_instance_log(
    mysql_host: str = Query(None, alias="地址"),
    mysql_port: str = Query(None, alias="端口"),
    db: Session = Depends(get_db)
):
    """
    查询方式：

    - 1、不传参
    - 2、只传入host
    - 3、传入host和port
    """
    if mysql_host is None and mysql_port is None:
        db_logs = crud.get_mysql_instance_log(db)
    elif mysql_host is not None and mysql_port is None:
        db_logs = crud.get_mysql_instance_log_by_host(db, host=mysql_host)
    elif mysql_host is not None and mysql_port is not None:
        db_logs = crud.get_mysql_instance_log_by_host_port(db, host=mysql_host, port=mysql_port)
    else:
        raise HTTPException(status_code=400, detail="Please pass in the correct parameters!")
    if db_logs:
        return db_logs
    else:
        raise HTTPException(status_code=404, detail="MySQL instance logs not found!")


#安装数据库实例
@app.post("/install_mysql_instance/", tags=["数据库操作"], summary="部署mysql实例")
def install_mysql_instance(
    mysql_project: str = Query(..., example="test", alias="项目"),
    mysql_host: str = Query(..., example="172.16.3.xx", alias="地址"),
    mysql_port: str = Query(..., example="3306", alias="端口"),
    mysql_password: str = Query(..., example="123456", alias="密码"),
    mysql_version: InstanceVersion = Query(..., alias="版本"),
    mysql_mark: str = Query(None, alias="备注"),
    disk_usage_gb: int = Query(..., example=10, alias="预计占用磁盘(GB)"),
    innodb_buffer_pool_size: str = Query(..., example='1G', alias="innodb_buffer_pool_size"),
    db: Session = Depends(get_db)
):
    """
    调用说明：

    - 1、只能在已加入本系统的宿主机部署MySQL实例
    - 2、如果是数据库目录单独一个LV，则预计占用磁盘决定LV的大小
    - 3、innodb_buffer_pool_size可以设置（M|G|MB|GB）为单位，MySQL数据库能识别即可
    """
    db_instance = crud.get_mysql_instance_by_host_port(db=db, host=mysql_host, port=mysql_port)
    if db_instance:
        return {"result":"MySQL instance Already installed"}
    db_server = crud.get_server_by_host(db=db, host=mysql_host)
    if db_server:
        #判断宿主机是否处于可用状态
        if db_server[0].server_status == "1":
            #更新server资源信息后，再次获取宿主机信息
            if not update_server(db=db, server_host=mysql_host):
                return {"result":"Update server info failed"}
            db_server = crud.get_server_by_host(db=db, host=mysql_host)
            if not db_server:
                return {"result":"Get server info failed"}
            memory_all = db_server[0].memory_all
            memory_free = db_server[0].memory_free
            disk_all = db_server[0].disk_all
            disk_free = db_server[0].disk_free
            #把输入的buffer_pool_size转化为以GB为单位的整数，以方便计算
            innodb_buffer_pool_size_num = re.findall(r"\d+\.?\d*", innodb_buffer_pool_size)
            if re.findall(r"(MB|mb|Mb|mB|M|m)", innodb_buffer_pool_size):
                innodb_buffer_pool_size_gb = int(innodb_buffer_pool_size_num[0])/1000
            elif re.findall(r"(GB|gb|Gb|gB|G|g)", innodb_buffer_pool_size):
                innodb_buffer_pool_size_gb = int(innodb_buffer_pool_size_num[0])
            else:
                innodb_buffer_pool_size_gb = int(innodb_buffer_pool_size_num[0])
            #判断宿主机内存是否足够
            if memory_free-0.2*memory_all-innodb_buffer_pool_size_gb<0:
                return {"result":"Server memory not enough"}
            #判断宿主机磁盘是否足够
            if db_server[0].lv_manage == "yes" and disk_free-disk_usage_gb<0:
                return {"result":"Server VG space not enough"}
            elif db_server[0].lv_manage == "no" and disk_free-0.3*disk_all-disk_usage_gb<0:
                return {"result":"Server disk part space not enough"}
            #如果是单独lv分区，则为实例预先创建lv分区
            if db_server[0].lv_manage == "yes" :
                disk_part = db_server[0].disk_part
                vg_name = db_server[0].vg_name
                lv_name = "mysql%s"%(mysql_port)
                lv_size = "%sG"%(disk_usage_gb)
                mount_dir = "%s/mysql/mysql%s"%(disk_part, mysql_port)
                if not lv_create(host=mysql_host, vg_name=vg_name, lv_name=lv_name, lv_size=lv_size, mount_dir=mount_dir):
                    return {"result":"LV create failed"}
            #开始部署MySQL实例
            cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s bash /mysql_install_files/mysql_install.sh %s %s %s %s %s'%(mysql_host, mysql_version.value, mysql_port, mysql_password, db_server[0].disk_part, innodb_buffer_pool_size)
            return_code = os.system(cmd)
            #安装成功与否交给脚本去判断，给一个准确的返回值就行
            if return_code == 0:
                #更新server资源信息
                update_server(db=db, server_host=mysql_host)
                #添加实例操作日志和mysql实例信息
                ins_log = {
                    "host":mysql_host,
                    "port":mysql_port, 
                    "action":"install", 
                    "action_result":1
                }
                instance = {
                    "mysql_project":mysql_project,
                    "mysql_version":mysql_version,
                    "mysql_host":mysql_host,
                    "mysql_port":mysql_port,
                    "mysql_password":mima.jiami(mysql_password),
                    "mysql_role":db_server[0].server_role,
                    "mysql_mark":mysql_mark,
                    "disk_usage_gb":disk_usage_gb,
                    "innodb_buffer_pool_size":innodb_buffer_pool_size
                }
                if crud.add_mysql_instance(db=db, instance=instance) and crud.add_log(db=db, log=ins_log):
                    return {"result":"Install MySQL instance successfully"}
                else:
                    return {"result":"Install MySQL instance successfully, but write to hmi system failed!"}
            else:
                #添加操作失败日志
                ins_log = {
                    "host":mysql_host,
                    "port":mysql_port, 
                    "action":"install", 
                    "action_result":0
                }
                crud.add_log(db=db, log=ins_log)
                return {"result":"Install MySQL instance failed"}
        else:
            return {"result":"Server status not allowed install MySQL instance "}
    else:
        raise HTTPException(status_code=404, detail="Server not found")


#删除数据库实例（删除主库完成时提示从库的存在）
@app.post("/remove_mysql_instance/", tags=["数据库操作"], summary="删除mysql实例")
def remove_mysql_instance(
    mysql_host: str = Query(..., example="172.16.3.xx", alias="地址"), 
    mysql_port: str = Query(..., example="3306", alias="端口"), 
    db: Session = Depends(get_db),
):
    """
    调用说明：

    - 1、慎重执行
    - 2、后端会自动停止数据库实例，然后删除对应数据目录
    """
    db_instance = crud.get_mysql_instance_by_host_port(db=db, host=mysql_host, port=mysql_port)
    if db_instance: 
        mysql_version = db_instance[0].mysql_version
        mysql_password = mima.jiemi(db_instance[0].mysql_password)
        cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s bash /mysql_install_files/mysql_remove.sh %s %s %s'%(mysql_host, mysql_version, mysql_port, mysql_password) 
        result_code = os.system(cmd)
        if result_code == 0:
            #如果是单独lv分区，则删除实例对应lv
            db_server = crud.get_server_by_host(db=db, host=mysql_host)
            if db_server[0].lv_manage == "yes" :
                vg_name = db_server[0].vg_name
                disk_part = db_server[0].disk_part
                lv_name = "mysql%s"%(mysql_port)
                mount_dir = "%s/mysql/mysql%s"%(disk_part, mysql_port)
                if not lv_remove(host=mysql_host, vg_name=vg_name ,lv_name=lv_name ,mount_dir=mount_dir):
                    {"result":"Remove MySQL instance LV failed"}
            #删除mysql实例信息
            crud.del_mysql_instance(db=db, host=mysql_host, port=mysql_port)
            #删除账号信息
            crud.del_user_by_host_port(db=db, host=mysql_host, port=mysql_port)
            #更新server资源信息
            update_server(db=db, server_host=mysql_host)
            #添加日志
            del_log = {
                "host":mysql_host,
                "port":mysql_port, 
                "action":"remove", 
                "action_result":1
            }
            crud.add_log(db=db, log=del_log)
            #判断其是否有从库，有则提示删除
            slave_instances = crud.get_ms_by_mhost_mport(db=db, host=mysql_host, port=mysql_port)
            slave_list = []
            if slave_instances:
                for slave_instance in slave_instances:
                    slave_list.append(slave_instance.slave_host + " : " +slave_instance.slave_port)
                return {"Remove MySQL instance successfully, Please remember remove slave instances": slave_list}
            else:
                crud.del_ms(db=db, host=mysql_host, port=mysql_port)
            return {"result":"Remove MySQL instance successfully"}
        else:
            #添加日志
            del_log = {
                "host":mysql_host,
                "port":mysql_port, 
                "action":"remove", 
                "action_result":0
            }
            crud.add_log(db=db, log=del_log)
            return {"result":"Remove MySQL instance failed!"}
    else:
        raise HTTPException(status_code=404, detail="MySQL instance not found!")


#查看主从信息
@app.get("/get_mysql_replication/", response_model=List[schemas.MS], tags=["主从操作"], summary="获取主从信息")
def get_mysql_replication(
    host: str = Query(None, alias="地址"),
    port: str = Query(None, alias="端口"),
    db: Session = Depends(get_db)
):
    """
    查询方式：

    - 1、不传参
    - 2、只传入host
    - 3、传入host和port
    """
    if host is None and port is None:
        ms = crud.get_ms(db)
    elif host is not None and port is None:
        ms = crud.get_ms_by_host(db=db, host=host)
    elif host is not None and port is not None:
        ms = crud.get_ms_by_host_port(db=db, host=host, port=port)
    else:
        raise HTTPException(status_code=400, detail="Please pass in the correct parameters!")
    if ms:
        return ms
    else:
        raise HTTPException(status_code=404, detail="Master and Slave info not found!")


#搭建主从
#@app.post("/config_mysql_replication/", tags=["主从操作"], summary="搭建主从（针对新实例）")
def config_mysql_replication(
    master_host: str = Query(..., example="172.16.3.xx", alias="主库地址"), 
    master_port: str = Query(..., example="3306", alias="主库端口"), 
    slave_host: str = Query(..., example="172.16.3.xx", alias="从库地址"), 
    slave_port: str = Query(..., example="3306", alias="从库端口"), 
    repl_type: ReplType = Query(..., alias="复制类型"), 
    db: Session = Depends(get_db),
):
    db_master = crud.get_mysql_instance_by_host_port(db=db, host=master_host, port=master_port)
    db_slave = crud.get_mysql_instance_by_host_port(db=db, host=slave_host, port=slave_port)
    #先判断主从实例是否存在
    if  db_master and not db_slave:
        raise HTTPException(status_code=404, detail="Slave instance not found!")
    elif not db_master and db_slave:
        raise HTTPException(status_code=404, detail="Master instance not found!")
    elif not db_master and not db_slave:
        raise HTTPException(status_code=404, detail="Master and Slave instance not found!")
    else:
        #根据实例版本约束复制[能否复制、复制类型]
        if db_master[0].mysql_version == '5.6':
            if db_slave[0].mysql_version != '5.6' and db_slave[0].mysql_version != '5.7':
                raise HTTPException(status_code=400, detail="Because the master is version 5.6, the slave can only be version 5.6 or 5.7")
            if repl_type == 'semi_sync':
                raise HTTPException(status_code=400, detail="Because the master is version 5.6, only async is supported")
        elif db_master[0].mysql_version == '5.7':
            if db_slave[0].mysql_version != '5.7' and db_slave[0].mysql_version != '8.0':
                raise HTTPException(status_code=400, detail="Because the master is version 5.7, the slave can only be version 5.7 or 8.0")
        elif db_master[0].mysql_version == '8.0':
            if db_slave[0].mysql_version != '8.0' :
                raise HTTPException(status_code=400, detail="Because the master is version 8.0, the slave can only be version 8.0")
        #根据机器角色去约束主从角色
        server_master = crud.get_server_by_host(db=db, host=master_host)
        server_slave = crud.get_server_by_host(db=db, host=slave_host)
        if server_master[0].server_role == 'master' and server_slave[0].server_role == 'slave':
            #开始调用脚本搭建主从
            master_cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s "bash /mysql_install_files/replication_config.sh master %s %s %s %s %s %s %s"'\
                %(master_host, repl_type.value, master_host, master_port, mima.jiemi(db_master[0].mysql_password), slave_host, slave_port, mima.jiemi(db_slave[0].mysql_password))
            slave_cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s "bash /mysql_install_files/replication_config.sh slave %s %s %s %s %s %s %s"'\
                %(slave_host, repl_type.value, master_host, master_port, mima.jiemi(db_master[0].mysql_password), slave_host, slave_port, mima.jiemi(db_slave[0].mysql_password))
            return_code1 = os.system(master_cmd)
            return_code2 = os.system(slave_cmd)
            if return_code1 == 0 and return_code2 == 0:
                ms = {
                    "master_host":master_host,
                    "master_port":master_port, 
                    "slave_host":slave_host,
                    "slave_port":slave_port, 
                    "repl_type":repl_type
                }
                crud.add_ms(db=db, ms=ms)
                return {"result": "Replication config successfully"}
            elif return_code1 != 0 and return_code2 == 0:
                return {"result": "Replication config failed at master!"}
            elif return_code1 == 0 and return_code2 != 0:
                return {"result": "Replication config failed at slave!"}
            else:
                return {"result": "Replication config failed on master and slave!"}
        else:
            raise HTTPException(status_code=400, detail="The master-slave relationship does not match the server role!")


#搭建从库
@app.post("/install_slave_instance/", tags=["主从操作"], summary="搭建从库")
def install_slave_instance(
    master_host: str = Query(..., example="172.16.3.xx", alias="主库地址"), 
    master_port: str = Query(..., example="3306", alias="主库端口"), 
    slave_host: str = Query(..., example="172.16.3.xx", alias="从库地址"), 
    slave_port: str = Query(..., example="3306", alias="从库端口"), 
    slave_version: InstanceVersion = Query(..., alias="从库版本"),
    repl_type: ReplType = Query(..., alias="复制类型"), 
    db: Session = Depends(get_db),
):
    """
    调用说明：

    - 1、根据主库的相关参数部署从库，并且建立主从关系
    - 2、要求主库为新实例或者主库拥有少量且完整的binlog
    - 3、从库只能与主库同版本或者比主库高一个版本
    - 4、复制类型分为异步、半同步，5.6版本不可搭建半同步复制
    """
    #先判断主库实例是否存在
    db_master = crud.get_mysql_instance_by_host_port(db=db, host=master_host, port=master_port)
    if not db_master:
        raise HTTPException(status_code=404, detail="Master instance not found!")
    else:
        #根据主库版本约束从库的版本和复制类型
        if db_master[0].mysql_version == '5.6':
            if slave_version != '5.6' and slave_version != '5.7':
                raise HTTPException(status_code=400, detail="Because the master is version 5.6, the slave can only be version 5.6 or 5.7")
            if repl_type == 'semi_sync':
                raise HTTPException(status_code=400, detail="Because the master is version 5.6, only async is supported")
        elif db_master[0].mysql_version == '5.7':
            if slave_version != '5.7' and slave_version != '8.0':
                raise HTTPException(status_code=400, detail="Because the master is version 5.7, the slave can only be version 5.7 or 8.0")
        elif db_master[0].mysql_version == '8.0':
            if slave_version != '8.0' :
                raise HTTPException(status_code=400, detail="Because the master is version 8.0, the slave can only be version 8.0")
        #根据机器角色判断能否部署
        server_master = crud.get_server_by_host(db=db, host=master_host)
        server_slave = crud.get_server_by_host(db=db, host=slave_host)
        if server_master[0].server_role != 'master' or server_slave[0].server_role != 'slave':
            raise HTTPException(status_code=400, detail="The master-slave relationship does not match the server role!")
        #部署从库实例
        mysql_project = db_master[0].mysql_project       #可能存在多个从库，这里考虑一下，要不要唯一化，不唯一的话，还可以根据项目名查询实例
        mysql_host = slave_host
        mysql_port = slave_port
        mysql_password = mima.jiemi(db_master[0].mysql_password)
        mysql_version = slave_version 
        mysql_mark = master_host + ":" + master_port + "的从库"
        disk_usage_gb = db_master[0].disk_usage_gb
        innodb_buffer_pool_size = db_master[0].innodb_buffer_pool_size
        install_mysql_instance(
            db=db,
            mysql_project=mysql_project,
            mysql_host=mysql_host,
            mysql_port=mysql_port,
            mysql_password=mysql_password,
            mysql_version=mysql_version,
            mysql_mark=mysql_mark,
            disk_usage_gb=disk_usage_gb,
            innodb_buffer_pool_size=innodb_buffer_pool_size
        )
        #判断从库实例是否安装成功
        db_slave = crud.get_mysql_instance_by_host_port(db=db, host=slave_host, port=slave_port)
        if not db_slave:
            raise HTTPException(status_code=404, detail="Slave instance install failed!")
        #调用脚本搭建主从
        master_cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s "bash /mysql_install_files/replication_config.sh master %s %s %s %s %s %s %s"'\
            %(master_host, repl_type.value, master_host, master_port, mima.jiemi(db_master[0].mysql_password), slave_host, slave_port, mima.jiemi(db_slave[0].mysql_password))
        slave_cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s "bash /mysql_install_files/replication_config.sh slave %s %s %s %s %s %s %s"'\
            %(slave_host, repl_type.value, master_host, master_port, mima.jiemi(db_master[0].mysql_password), slave_host, slave_port, mima.jiemi(db_slave[0].mysql_password))
        return_code1 = os.system(master_cmd)
        return_code2 = os.system(slave_cmd)
        if return_code1 == 0 and return_code2 == 0:
            ms = {
                "master_host":master_host,
                "master_port":master_port, 
                "slave_host":slave_host,
                "slave_port":slave_port, 
                "repl_type":repl_type
            }
            crud.add_ms(db=db, ms=ms)
            return {"result": "Replication config successfully"}
        elif return_code1 != 0 and return_code2 == 0:
            return {"result": "Replication config failed at master!"}
        elif return_code1 == 0 and return_code2 != 0:
            return {"result": "Replication config failed at slave!"}
        else:
            return {"result": "Replication config failed on master and slave!"}


#获取用户授权信息
@app.get("/get_user/", response_model=List[schemas.UserBase], tags=["授权操作"], summary="获取授权信息")
def get_user(
    server_host: str = Query(..., example="172.16.3.xx", alias="数据库地址"), 
    server_port: str = Query(..., example="3306", alias="数据库端口"), 
    client_user: str = Query(None, alias="用户名"), 
    client_host: str = Query(None, alias="授权地址"),
    db: Session = Depends(get_db),
):
    """
    查询方式：

    - 1、传入数据库地址、数据库端口
    - 2、传入数据库地址、数据库端口、用户名
    - 3、传入数据库地址、数据库端口、授权地址
    - 4、传入数据库地址、数据库端口、用户名、授权地址
    """
    if server_host and server_port and not client_user and not client_host:
        users = crud.get_user_by_host_port(db=db, host=server_host, port=server_port)
    elif server_host and server_port and client_user and not client_host:
        users = crud.get_user_by_host_port_user(db=db, host=server_host, port=server_port, user=client_user)
    elif server_host and server_port and not client_user and client_host:
        users = crud.get_user_by_host_port_chost(db=db, host=server_host, port=server_port, chost=client_host)
    elif server_host and server_port and client_user and client_host:
        users = crud.get_user_by_host_port_user_chost(db=db, host=server_host, port=server_port, user=client_user, chost=client_host)
    else:
        raise HTTPException(status_code=400, detail="Please pass in the correct parameters!")
    if users:
        return users
    else:
        raise HTTPException(status_code=404, detail="User info not found!")


#授权新用户
@app.post("/grant_user/", tags=["授权操作"], summary="授权用户")
def grant_user(
    server_host: str = Query(..., example="172.16.3.xx", alias="数据库地址"), 
    server_port: str = Query(..., example="3306", alias="数据库端口"), 
    db_table: str = Query(..., example="test.*", alias="授权库.表"),
    client_user: str = Query(..., alias="用户名"),
    client_host: str = Query(..., alias="用户地址"), 
    client_pass: str = Query(..., alias="用户密码"), 
    user_role: UserRole = Query(..., alias="用户角色"), 
    db: Session = Depends(get_db),
):
    """
    调用说明：

    - 1、用户地址可以输入多个，用英文逗号（,）分隔
    - 2、用户角色分为只读（select）和读写（all）
    - 3、如果其中一个用户已存在，那么所有授权都不会进行
    """
    db_instance = crud.get_mysql_instance_by_host_port(db=db, host=server_host, port=server_port)
    if db_instance:
        server_pass = mima.jiemi(db_instance[0].mysql_password)
    else:
        raise HTTPException(status_code=404, detail="The instance not found in hmi system!")
    #从库不允许授权用户
    if crud.get_ms_by_host_port(db=db, host=server_host, port=server_port):
        if not crud.get_ms_by_mhost_mport(db=db, host=server_host, port=server_port):
            raise HTTPException(status_code=400, detail="Slave instance can't grant user!")
    chs = client_host.split(',')
    mycmds = ""
    for ch in chs:
        #判断是否已有此用户
        db_user=crud.get_user_by_host_port_user_chost(db=db, host=server_host, port=server_port, user=client_user, chost=ch)
        if db_user:
            raise HTTPException(status_code=400, detail="'%s'@'%s' already exists!"%(client_user, ch))
        #拼接授权语句
        mycmd = "create user '%s'@'%s' identified by '%s';"\
            %(client_user, ch, client_pass)
        if user_role == "readonly":
            mycmd = mycmd + "grant select on %s to '%s'@'%s';"%(db_table, client_user, ch)
        elif user_role == "readwrite":
            mycmd = mycmd + "grant all on %s to '%s'@'%s';"%(db_table, client_user, ch)
            #mycmd = mycmd + "revoke drop on %s from '%s'@'%s';"%(db_table, client_user, ch)
        mycmds = mycmds + mycmd
    cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s "/usr/local/mysql/bin/mysql -h127.0.0.1 -P%s -uroot -p%s -e \\"%s\\""'\
        %(server_host, server_port, server_pass, mycmds)
    #print(cmd)
    return_code = os.system(cmd)
    if return_code == 0:
        for ch in chs:
            user = {
                "server_host": server_host,
                "server_port": server_port,
                "db_tb": db_table,
                "client_user": client_user,
                "client_host": ch,
                "client_pass": client_pass,
                "user_role": user_role,
            }
            crud.add_user(db=db, user=user)
        #从库授权信息的插入
        slave_instances = crud.get_ms_by_mhost_mport(db=db, host=server_host, port=server_port)
        for slave_instance in slave_instances:
            for ch in chs:
                user = {
                    "server_host": slave_instance.slave_host,
                    "server_port": slave_instance.slave_port,
                    "db_tb": db_table,
                    "client_user": client_user,
                    "client_host": ch,
                    "client_pass": client_pass,
                    "user_role": user_role,
                }
                crud.add_user(db=db, user=user)
        return {"result":"Grant user successfully"}
    else:
        return {"result":"Grant user failed!"}


#用户删除
@app.post("/drop_user/", tags=["授权操作"], summary="删除用户")
def drop_user(
    server_host: str = Query(..., example="172.16.3.xx", alias="数据库地址"), 
    server_port: str = Query(..., example="3306", alias="数据库端口"), 
    client_user: str = Query(..., alias="用户名"), 
    client_host: str = Query(..., alias="用户地址"), 
    db: Session = Depends(get_db)
):
    """
    调用说明：

    - 1、用户地址可以输入多个，用英文逗号（,）分隔
    - 2、如果其中一个用户不存在，那么所有用户删除操作都不会进行
    """
    db_instance = crud.get_mysql_instance_by_host_port(db=db, host=server_host, port=server_port)
    if db_instance:
        server_pass = mima.jiemi(db_instance[0].mysql_password)
    else:
        raise HTTPException(status_code=404, detail="The instance not found in hmi system")
    #从库不允许删除用户
    if crud.get_ms_by_host_port(db=db, host=server_host, port=server_port):
        if not crud.get_ms_by_mhost_mport(db=db, host=server_host, port=server_port):
            raise HTTPException(status_code=400, detail="Slave instance can't drop user!")
    chs = client_host.split(',')
    mycmds = ""
    for ch in chs:
        #判断是否有此用户
        db_user=crud.get_user_by_host_port_user_chost(db=db, host=server_host, port=server_port, user=client_user, chost=ch)
        if not db_user:
            raise HTTPException(status_code=400, detail="'%s'@'%s' not exists!"%(client_user, ch))
        mycmd = "drop user '%s'@'%s';"%(client_user, ch)
        mycmds = mycmds + mycmd
    cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s "/usr/local/mysql/bin/mysql -h127.0.0.1 -P%s -uroot -p%s -e \\"%s\\""'\
        %(server_host, server_port, server_pass, mycmds)
    print(cmd)
    return_code = os.system(cmd)
    if return_code == 0:
        for ch in chs:
            crud.del_user(db=db, host=server_host, port=server_port, user=client_user, chost=ch)
        #从库授权信息的删除
        slave_instances = crud.get_ms_by_mhost_mport(db=db, host=server_host, port=server_port)
        for slave_instance in slave_instances:
            for ch in chs:
                crud.del_user(db=db, host=slave_instance.slave_host, port=slave_instance.slave_port, user=client_user, chost=ch)
        return {"result":"Drop user successfully"}
    else:
        return {"result":"Drop user failed!"}


#实例LV扩容
@app.post("/extend_mysql_instance_lv/", tags=["数据库操作"], summary="实例LV扩容")
def extend_mysql_instance_lv(
    host: str = Query(..., example="172.16.3.xx", alias="地址"),
    port: str = Query(..., example="3306", alias="端口"),
    lv_size: str = Query(..., example="10G", alias="LV容量"),
    db: Session = Depends(get_db)
):
    """
    调用说明：

    - 1、指定实例的地址和端口，即可扩容对应实例的数据目录
    - 2、LV容量指的是新增的容量
    """
    if not update_server(db=db, server_host=host):
        return {"result":"Update server info failed"}
    db_server = crud.get_server_by_host(db=db, host=host)
    if not db_server:
        return {"result":"Get server info failed"}
    #判断是否为lv实例
    if db_server[0].lv_manage != 'yes':
        return {"result":"The instance is not manage by lv"}
    else:
        db_instance = crud.get_mysql_instance_by_host_port(db=db, host=host, port=port)
        if not db_instance:
            return {"result":"The instance is not exists"}
    #判断是否容量还够
    lv_size_list = re.findall(r"\d+\.?\d*", lv_size)
    lv_size_gb = int(lv_size_list[0])
    disk_free = db_server[0].disk_free
    if disk_free-lv_size_gb<=0:
        return {"result":"VG not enough, free VG: %sG"%(disk_free)}
    #LV扩容
    vg_name = db_server[0].vg_name
    lv_name = "mysql%s"%(port)
    cmd = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s bash /mysql_install_files/lv_manage.sh extend %s %s %s"\
        %(host, vg_name, lv_name, lv_size)
    return_code = os.system(cmd)
    if return_code == 0:
        if update_server(db=db, server_host=host):
            return {"result":"LV extend successfully"}
        else:
            return {"result":"LV extend successfully, but update server info failed"}
    else:
        return {"result":"LV extend failed"}
