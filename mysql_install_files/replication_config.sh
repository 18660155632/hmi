#!/bin/bash

#用于搭建主从
#例子：bash replication_config.sh master async 172.16.1.25 3306 123456 172.16.1.26 3306 123456


master(){
    echo "drop user 'repl'@'${master_host}';
          drop user 'repl'@'${slave_host}';
          create user 'repl'@'${master_host}' identified by 'repl';
          create user 'repl'@'${slave_host}' identified by 'repl';
          grant replication slave,replication client on *.* to 'repl'@'${master_host}';
          grant replication slave,replication client on *.* to 'repl'@'${slave_host}';
    " > /mysql_install_files/master.sql
    if [[ ${repl_type} == "semi_sync" ]]
    then
        echo "set global rpl_semi_sync_master_enabled = 1;" >> /mysql_install_files/master.sql
        cnf=$(find / -name my.cnf | grep ${master_port})
        #修改配置文件
        sed -i 's/loose-rpl_semi_sync_master_enabled.*/loose-rpl_semi_sync_master_enabled = 1/g' ${cnf}
    fi
    /usr/local/mysql/bin/mysql -h127.0.0.1 -P${master_port} -uroot -p${master_password} -f </mysql_install_files/master.sql || exit 1
}

slave(){
    echo "stop slave;
          reset master;
          reset slave all;
          set global read_only=1;
          change master to master_host='${master_host}',master_port=${master_port},master_user='repl',master_password='repl',master_auto_position=1;
          start slave;
    " > /mysql_install_files/slave.sql
    cnf=$(find / -name my.cnf | grep ${slave_port})
    if [[ ${repl_type} == "semi_sync" ]]
    then
        echo "set global rpl_semi_sync_slave_enabled = 1;" >> /mysql_install_files/slave.sql
        #修改配置文件
        sed -i 's/loose-rpl_semi_sync_slave_enabled.*/loose-rpl_semi_sync_slave_enabled = 1/g' ${cnf}
    fi
    /usr/local/mysql/bin/mysql -h127.0.0.1 -P${slave_port} -uroot -p${slave_password} </mysql_install_files/slave.sql || exit 1
    #修改配置文件
    sed -i 's/#read_only.*/read_only = 1/g' ${cnf}
    /usr/local/mysql/bin/mysql -h127.0.0.1 -P${slave_port} -uroot -p${slave_password} -e "show slave status\G" | grep "Running:" | grep -i "No"
    if (($?==0))
    then
       exit 1
    fi
}


main(){
    if (($#==8))
    then
	    repl_role=$1
	    repl_type=$2
	    master_host=$3
	    master_port=$4
	    master_password=$5
	    slave_host=$6
	    slave_port=$7
	    slave_password=$8
	    if [[ ${repl_role} == 'master' ]]
	    then
		master
	    elif [[ ${repl_role} == 'slave' ]]
	    then
		slave
	    else
		exit 1
	    fi
    else
            exit 1
    fi
}

main $1 $2 $3 $4 $5 $6 $7 $8
