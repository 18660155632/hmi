#!/bin/bash

### MySQL实例删除脚本
### 位置参数：	$1：版本号
###		$2：端口号	
###		$3：本地root密码
### 使用示例：bash mysql_remove.sh 8.0 3306 123456
### 要求：需要是mysql_install.sh脚本安装的实例才能用此脚本删除，因为它依赖一些路径及目录名形式


#关闭数据库
shutdown(){
	ps aux | grep ${port} | grep -v "grep" >/dev/null
	if (($?==0))
	then
		/opt/mysql/mysql-${version}*/bin/mysqladmin -h127.0.0.1 -P${port} -uroot -p${pass} shutdown 2>/dev/null
	fi
}


#删除数据库文件
remove(){
	#如果数据库对应的lv存在，那么就不删除，交给lv删除函数去做
	lvs | grep mysql${port} &>/dev/null
	if (($?==0))
	then
		echo "---数据库所在LV待删除"
		exit 0
	fi
	filedir=$(find / -name "mysql${port}")
	rm -rf ${filedir} 
        if (($?==0))
        then
        	echo "---数据库删除成功"
        else
        	echo "---数据库删除失败！"
		exit 1
        fi
}


#参数输入
datain(){
	if (($#==3))
	then
		version=$1
		port=$2
		pass=$3
	else
		echo "请输入要删除的实例信息"
		read -p "版本号(5.6/5.7/8.0)：" version
		read -p "端口号：" port
		read -p "root密码：" pass
	fi
	if [[ ${version} != '5.6' ]] && [[ ${version} != '5.7' ]] && [[ ${version} != '8.0' ]]
        then
		echo "---不支持此版本实例卸载！"
                exit 1
        fi
}


main(){
	datain $1 $2 $3
	shutdown
	sleep 20
	remove
}



main $1 $2 $3
