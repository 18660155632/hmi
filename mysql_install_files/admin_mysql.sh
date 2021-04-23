#!/bin/bash

#负责多版本MySQL实例的启动、关闭、重启、存活检查

RED='\E[1;31m'      # 红
GREEN='\E[1;32m'    # 绿
YELLOW='\E[1;33m'   # 黄
BLUE='\E[1;34m'     # 蓝
RES='\E[0m'         # 清除颜色

instance_part='/data'	#实例文件主目录


#查看实例存活状态
status_mysql(){
	if [[ ${port} == '' ]]
	then
		ports=($(ls ${instance_part}/mysql | awk -Fmysql '{print $2}'))
		for port in ${ports[@]}
		do
			ps aux | grep mysql${port}.pi[d] &>/dev/null && netstat -ntpul | grep ${port} &>/dev/null
			if (($?==0))
        		then
				echo -e "---${port} [${GREEN}ok${RES}]"
			else
				echo -e "---${port} [${RED}dead${RES}]"
			fi
		done
		exit 0
	else
		ps aux | grep mysql${port}.pi[d] &>/dev/null && netstat -ntpul | grep ${port} &>/dev/null
		if (($?==0))
		then
			/opt/mysql/mysql-${version}*/bin/mysql -h127.0.0.1 -P${port} -uroot -p${password} -e "select 1;" &>/dev/null
			if (($?==0))
			then
				echo -e "---${port} ${GREEN}[ok]${RES}"
				return 0
			else
				echo "---${port} ${YELLOW}[warning]${RES}"
				return 1
			fi
		else
			echo -e "---${port} ${RED}[dead]${RES}"
			return 1
		fi
	fi
}

#启动数据库实例
start_mysql(){
	echo "---${port} ready to start..."
	if status_mysql &>/dev/null
	then
		echo -e "---${BLUE}${port} is already alive!${RES}"
	else
		/opt/mysql/mysql-${version}*/bin/mysqld_safe --defaults-file=/data/mysql/mysql${port}/conf/my.cnf &
		sleep 5
		if status_mysql &>/dev/null
		then
			echo -e "---${GREEN}${port} start successfully!${RES}"
		else
			echo -e "---${RED}${port} start failed!${RES}"
		fi
	fi
}

#关闭数据库实例
stop_mysql(){
	echo "---${port} ready to shutdown..."
	if status_mysql &>/dev/null
	then
		/opt/mysql/mysql-${version}*/bin/mysqladmin -h127.0.0.1 -P${port} -uroot -p${password} shutdown 
		sleep 5
		if status_mysql &>/dev/null
                then
                        echo -e "---${RED}${port} shutdown failed!${RES}"
                else
                        echo -e "---${GREEN}${port} shutdown successfully!${RES}"
                fi
	else
		echo -e "---${BLUE}${port} is already shutdown!${RES}"
	fi
}

#输入参数
datain(){
	if [[ $1 == '-h' ]] || [[ $1 == '--help' ]] || [[ $1 == '' ]]
	then
		echo "Usage: ./admin_mysql [action] [port] [password]"
		echo "Example: "
		echo "       ./admin_mysql status"
		echo "       ./admin_mysql stop 3306 123456"
		echo "       ./admin_mysql start 3306 123456"
		echo "       ./admin_mysql restart 3306 123456"
		exit
	fi
	action=$1
	port=$2
	password=$3
	if [[ ${action} == "status" ]]
	then
		status_mysql	
	fi
	version=$(awk '{print $2}' ${instance_part}/mysql/mysql${port}/version 2>/dev/null)
	rm -f /usr/local/mysql
	ln -s /opt/mysql/mysql-${version}* /usr/local/mysql
	if [[ ${action} == "start" ]]
	then
		start_mysql
	elif [[ ${action} == "stop" ]]
	then
		stop_mysql
	elif [[ ${action} == "restart" ]]
	then
		stop_mysql && start_mysql
	else
		echo "Bad input"
	fi
}

datain $@

