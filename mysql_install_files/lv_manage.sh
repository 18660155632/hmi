#!/bin/bash

#使用示例：
#   创建lv：./lvm_manage.sh create datavg mysql3306 10G /data/mysql/mysql3306
#   删除lv：./lvm_manage.sh remove datavg mysql3306 /data/mysql/mysql3306
#   扩容lv：./lvm_manage.sh extend datavg mysql3306 10G


#创建lv
lv_create(){
    #判断LV是否已存在
    if [ -e /dev/${vg_name}/${lv_name} ]
    then
        echo "---LV已存在"
        exit 1
    fi
    #判断剩余VG容量是否够分配
    vg_free_gb=$(vgs --units g | grep ${vg_name} |awk '{print $NF}' | awk -Fg '{print $1}')
    lv_size_gb=$(echo ${lv_size} | awk -F[gG] '{print $1}')
    if ((${vg_free_gb%.*}<${lv_size_gb%.*}))
    then
        echo "---VG容量不足，VG剩余${vg_free_gb}G"
        exit 1
    fi
    #判断想要挂载点是否已存在，不存在则创建
    if [ -e ${mount_dir} ]
    then
        echo "---该挂载点已存在"
        exit 1
    else
        mkdir -p ${mount_dir} 
    fi
    lvcreate -L ${lv_size} -n ${lv_name} ${vg_name} -y
    if (($?!=0))
    then
        echo "---LV创建失败"
        exit 1
    fi
    mkfs -t xfs /dev/${vg_name}/${lv_name} &>/dev/null || exit 1
    mount /dev/${vg_name}/${lv_name} ${mount_dir} || exit 1
    echo "/dev/${vg_name}/${lv_name} ${mount_dir} xfs defaults 0 0" >>/etc/fstab || exit 1
    echo "---LV创建成功"
}


#删除lv
lv_remove(){
    #判断LV是否已存在，不存在则退出
    if [ ! -e /dev/${vg_name}/${lv_name} ]
    then
        echo "---LV不存在"
        exit 1
    fi
    #判断想要挂载点是否存在，不存在则退出
    if [ ! -e ${mount_dir} ]
    then
        echo "---挂载点不存在"
        exit 1
    fi   
    umount ${mount_dir} || exit 1
    sed -i "/${lv_name}/d" /etc/fstab || exit 1
    lvremove -f ${vg_name}/${lv_name} &>/dev/null || exit 1
    rm -rf ${mount_dir} || exit 1
    echo "---LV删除成功"
}


#扩容lv
lv_extend(){
    #判断剩余VG容量是否够分配
    vg_free_gb=$(vgs --units g | grep ${vg_name} |awk '{print $NF}' | awk -Fg '{print $1}')
    lv_size_gb=$(echo ${lv_size} | awk -F[gG] '{print $1}')
    if ((${vg_free_gb%.*}<${lv_size_gb%.*}))
    then
        echo "---VG容量不足，VG剩余${vg_free_gb}G"
        exit 1
    fi
    #判断LV是否已存在，不存在则退出
    if [ ! -e /dev/${vg_name}/${lv_name} ]
    then
        echo "---LV不存在"
        exit 1
    fi
    lvextend -L +${lv_size} /dev/${vg_name}/${lv_name} || exit 1
    xfs_growfs /dev/${vg_name}/${lv_name} &>/dev/null || exit 1
    echo "---LV扩容成功"
}



datain(){
    action=$1
    vg_name=$2
    lv_name=$3
    if [[ ${action} == 'create' ]]
    then
        lv_size=$4
        mount_dir=$5
        lv_create
    elif [[ ${action} == 'remove' ]]
    then
        mount_dir=$4
        lv_remove
    elif [[ ${action} == 'extend' ]]
    then
        lv_size=$4
        lv_extend
    else
        exit 1
    fi   
}

datain $@
