import os


#创建LV
def lv_create(host: str, vg_name: str, lv_name: str, lv_size: str, mount_dir: str):
    cmd = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s bash /mysql_install_files/lv_manage.sh create %s %s %s %s"\
        %(host, vg_name, lv_name, lv_size, mount_dir)
    return_code = os.system(cmd)
    if return_code == 0:
        return True
    else:
        return False


#删除LV
def lv_remove(host: str, vg_name: str, lv_name: str, mount_dir: str):
    cmd = "ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@%s bash /mysql_install_files/lv_manage.sh remove %s %s %s"\
        %(host, vg_name, lv_name, mount_dir)
    return_code = os.system(cmd)
    if return_code == 0:
        return True
    else:
        return False
