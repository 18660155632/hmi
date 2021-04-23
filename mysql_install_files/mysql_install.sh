#!/usr/bin/bash

### <MySQL免编译安装脚本>
### 请把【安装脚本】、【配置文件】、【MySQL免编译软件包】放在同一目录 (同一大版本的MySQL安装包只可以放一个)
### 位置参数：
###	$1=版本号
###	$2=端口号
###	$3=ROOT密码
###	$4=主存储磁盘分区
###	$5=innodb_buffer_pool_size(带单位)
### 软件路径：/opt/mysql/mysql-X.X.XX-linux-glibc2.5-x86_64 (软链到/usr/local/mysql)
### 数据集中目录：/${part}/mysql/mysql33XX (part变量取自配置文件，初始化数据库目录到任意磁盘分区只需要修改配置文件)
### 时间：2021-2-5


depend(){		#安装依赖包
	if rpm -q libaio &>>${dir}/mysql${port}_install.log
	then
		echo '---libaio已安装'
	else
		yum install -y libaio &>>${dir}/mysql${port}_install.log
		echo '---libaio安装完毕'
	fi

	if rpm -q autoconf &>>${dir}/mysql${port}_install.log
	then
		echo '---autoconf已安装'
	else
		yum install -y autoconf &>>${dir}/mysql${port}_install.log
		echo '---autoconf安装完毕'
	fi
}

untar(){		#解压安装包
	mkdir -p /opt/mysql
	tar_name=$(ls ${dir} | egrep mysql-${version}.*tar)
	name=$(echo ${tar_name} | awk -F'/' '{print $NF}' | awk -F'.tar' '{print $1}')	#获取解压后的安装包目录名
	if [ -d "/opt/mysql/${name}" ]
	then
		echo '---此版本MySQL已安装'
	elif [ -f "${dir}/${tar_name}" ]
	then
		echo '---正在解压MySQL安装包'
		tar xf ${dir}/${tar_name} -C /opt/mysql &>/dev/null
	else
		echo '---MySQL软件压缩包不存在！'
		exit 1
	fi
	rm -rf /usr/local/mysql
	ln -s /opt/mysql/${name} /usr/local/mysql		#建立软链接，让此版本为mysql启动版本
}

user(){			#创建mysql用户
	if id mysql >>${dir}/mysql${port}_install.log
	then
		echo '---mysql用户已创建'
	else
		groupadd mysql
		useradd -M -g mysql -s /sbin/nologin -d /usr/local/mysql mysql && echo '---mysql用户创建成功'
	fi
}

path(){			#加入path路径
	source /etc/profile
	if echo $PATH | grep '/usr/local/mysql/bin' &>>${dir}/mysql${port}_install.log
	then
		echo '---PATH路径已添加'
	else
		echo "export PATH=$PATH:/usr/local/mysql/bin">>/etc/profile
		source /etc/profile
		if echo $PATH | grep '/usr/local/mysql/bin' &>>${dir}/mysql${port}_install.log
		then
			echo '---PATH路径添加成功'
		else
			echo '---PATH路径添加失败！'
			exit 1
		fi
	fi
}

cnf(){          #创建目录、修改配置文件
	if [ -d "/${part}/mysql/mysql${port}" ] && (($(du -s /${part}/mysql/mysql${port} | awk '{print $1}')>0))
	then
		echo '---此端口的数据目录已存在，请检查！'
		exit 1
	else
		mkdir -p /${part}/mysql/mysql${port}/{data,logs,tmp,conf}
		echo "version: ${version}" >>/${part}/mysql/mysql${port}/version
		echo '---数据目录创建成功'              
	fi
	cp ${dir}/${version}my.cnf /${part}/mysql/mysql${port}/conf/my.cnf
	sed -i 's/33[0-9][0-9]/'${port}'/g' /${part}/mysql/mysql${port}/conf/my.cnf
	server_id=$(ip a | grep -w inet | grep -v "127.0.0.1" | head -1 | awk -F'[./]' '{print $4}')${port}
	report_host=$(ip a | grep -w inet | grep -v "127.0.0.1" | head -1 | awk -F/ '{print $1}' | awk '{print $2}')
	sed -i 's/server_id.*/server_id = '${server_id}'/g' /${part}/mysql/mysql${port}/conf/my.cnf
	sed -i 's/report_host.*/report_host = '${report_host}'/g' /${part}/mysql/mysql${port}/conf/my.cnf
	sed -i 's/innodb_buffer_pool_size.*/innodb_buffer_pool_size = '${ibpool_size}'/g' /${part}/mysql/mysql${port}/conf/my.cnf
	sed -i "s/\/data\//\/${part}\//" /${part}/mysql/mysql${port}/conf/my.cnf
	echo '---配置文件复制并修改完毕'
}

own(){          #更改文件属主
	chown -R mysql:mysql /${part}/mysql/mysql${port}
	chown -R mysql:mysql /usr/local/mysql
	chown -R mysql:mysql /opt/mysql
}

init(){			#数据库实例初始化
	if [[ ${version} = "5.6" ]]
	then
		echo "---${version}版本的初始化..."
		/usr/local/mysql/scripts/mysql_install_db --defaults-file=/${part}/mysql/mysql${port}/conf/my.cnf --user=mysql \
		--basedir=/usr/local/mysql --datadir=/${part}/mysql/mysql${port}/data &>>${dir}/mysql${port}_install.log && echo '---数据库初始化成功'
	else
		echo "---${version}版本的初始化..."		#配置文件的选项要放在最前，不然不识别
		/usr/local/mysql/bin/mysqld --defaults-file=/${part}/mysql/mysql${port}/conf/my.cnf --initialize-insecure --user=mysql \
		--basedir=/usr/local/mysql --datadir=/${part}/mysql/mysql${port}/data &>>${dir}/mysql${port}_install.log && echo '---数据库初始化成功'
	fi
}

startserver(){		#启动数据库
	/usr/local/mysql/bin/mysqld_safe --defaults-file=/${part}/mysql/mysql${port}/conf/my.cnf &>>${dir}/mysql${port}_install.log & <<EOF
\r
EOF
	sleep 10
	if netstat -ntpul | grep ${port} &>>${dir}/mysql${port}_install.log
	then
		echo '---mysql启动成功'
	else
		echo '---mysql启动失败,等待再次检查中...'
		sleep 10
		if netstat -ntpul | grep ${port} &>>${dir}/mysql${port}_install.log
		then
			echo '---mysql启动成功'
		else
			echo '数据库启动失败！'
			echo '错误日志如下：'
			tail -100 /${part}/mysql/mysql${port}/logs/mysql-error.log | grep -i 'error'
			exit 1
		fi
	fi
}

expec(){		#安装expect自动化交互工具
	if rpm -q expect &>>${dir}/mysql${port}_install.log 
	then
		echo "---expect已安装"
	else
		yum install expect -y &>>${dir}/mysql${port}_install.log
		echo "---expect安装完毕"
	fi

	if rpm -q tcl-devel &>>${dir}/mysql${port}_install.log
	then
		echo "---tcl-devel已安装"
	else
		yum install tcl-devel -y &>>${dir}/mysql${port}_install.log
		echo "---tcl-devel安装完毕"
	fi
}

safe(){			#执行安全脚本
	rm -f /tmp/mysql.sock
	ln -s /${part}/mysql/mysql${port}/tmp/mysql${port}.sock /tmp/mysql.sock
	expec
	echo '---执行安全脚本并初始化密码...'
	expect &>>${dir}/mysql${port}_install.log <<EOF
	set timeout 5
	spawn mysql_secure_installation
	expect {
		"Press y|Y for Yes, any other key for No:" {send "n\n" ; exp_continue}
		"(Press y|Y for Yes, any other key for No) :" {send "y\n" ; exp_continue}
		"Enter current password for root (enter for none):" {send "\n" ; exp_continue}
		"New password:" {send "$pwd\n" ; exp_continue}   
		"Re-enter new password:" {send "$pwd\n" ; exp_continue}           
		"n]" {send "y\n" ; exp_continue}
	}
EOF
	if [[ ${version} = '5.6' ]] 
	then
		sql="reset master;"
	elif [[ ${version} = '5.7' ]] 
	then
		sql="grant all on *.* to 'root'@'127.0.0.1' identified by '${pwd}' with grant option;reset master;"
	elif [[ ${version} = '8.0' ]] 
	then
		sql="create user 'root'@'127.0.0.1' identified by '${pwd}';grant all on *.* to 'root'@'127.0.0.1' with grant option;reset master;"
	fi
	/usr/local/mysql/bin/mysql -S/${part}/mysql/mysql${port}/tmp/mysql${port}.sock -uroot -p${pwd} -e "${sql}" &>>${dir}/mysql${port}_install.log
	echo "---所有操作完成，请登录：mysql -h127.0.0.1 -P${port} -uroot -p${pwd}"
}


check(){		#安装后的检查
        ps aux | grep "mysqld" | grep "mysql${port}" >/dev/null
        if (($?==0))
        then
                /usr/local/mysql/bin/mysql -h127.0.0.1 -P${port} -uroot -p${pwd} -e "select 1;" &>/dev/null
                if (($?==0))
                then
                        echo "---数据库登录测试成功"
                else
                        echo "---数据库登录测试失败！"
                        exit 1
                fi
        else
                echo "---数据库线程不存在！"
                exit 1
        fi
}


install(){		#安装
	depend
	untar
	user
	path
	cnf
	own
	init
	startserver
	safe 
	check
}



datain(){		#输入部署信息
	if (($#==5))
	then
		version=$1
		port=$2
		pwd=$3
		part=$4
		ibpool_size=$5
	else
		echo '请把[软件包]、[安装脚本]、[配置文件]放在同一目录'
		read -p '请输入版本号(5.6/5.7/8.0)：' version
		read -p '请输入端口号：' port
		read -p '请定义ROOT密码：' pwd
		read -p '请输入主磁盘分区：' part
		read -p '请输入innodb_buffer_pool_size：' ibpool_size
	fi
	
	if [[ ${version} != '5.6' ]] && [[ ${version} != '5.7' ]] && [[ ${version} != '8.0' ]]
	then
        	echo '---此脚本仅支持MySQL5.6、5.7、8.0的安装！'
        	exit 1
	fi
	if netstat -ntpul | grep ${port} &>${dir}/mysql${port}_install.log
	then
		echo '---此端口已被使用！'
		exit 1
	fi
	#修改一下磁盘分区位置格式
	if [[ ${part} == '/' ]]
	then
		part='data'
	else
		part=${part:1}
	fi
	#通过配置文件获取主磁盘分区（弃用，改为按用户输入，去修改配置文件）
	#part=$(grep '^datadir' ${dir}/${version}my.cnf | awk -F'[=/]' '{print $3}')
	install
}

#安装脚本、软件包、配置文件位置
dir="/mysql_install_files"

datain $1 $2 $3 $4 $5
