#!/bin/bash

### 初始化服务器参数使其适配MySQL(centos7专用)
### 包括：selinux、firewall、numa、swappiness、io调度算法、最大进程数、最大文件打开数

#关闭selinux
selinux(){
	setenforce 0 &>/dev/null
	sed -i 's/SELINUX.*=.*enforcing/SELINUX=disabled/g' /etc/selinux/config
}

#关闭防火墙
firewall(){
	systemctl stop firewalld &>/dev/null
	systemctl disable firewalld &>/dev/null
}

#关闭numa
numa(){
	num=$(numactl --hardware | awk '/^available/{print $2}')
	if (($?!=0))
	then
		yum install numactl -y &>/dev/null || exit 1
		num=$(numactl --hardware | awk '/^available/{print $2}')
	fi
	if ((${num}!=1))
	then
		numactl --interleave=all &>/dev/null || exit 1
		sed -i '/GRUB_CMDLINE_LINUX=/{s/"$/ numa=off"/g}' /etc/default/grub &>/dev/null
		grub2-mkconfig -o /etc/grub2.cfg &>/dev/null || exit 1
	fi
}

#调整swap使用
swap(){
	sysctl vm.swappiness=1 &>/dev/null
	grep "vm.swappiness=1" /etc/sysctl.conf &>/dev/null
	if (($?!=0))
	then
		echo "vm.swappiness=1" >>/etc/sysctl.conf
	fi
}

#调整io调度算法
io(){
	cat /sys/block/sda/queue/scheduler | grep -w '\[deadline\]' &>/dev/null
	if (($?!=0))
	then
		echo "deadline">/sys/block/sda/queue/scheduler
		grubby --update-kernel=ALL --args="elevator=deadline" &>/dev/null || exit 1
	fi
}

#最大文件打开数/用户最大线程数
limits(){
	if (($(ulimit -n)!=102400))
	then
		echo "* - nofile 102400" >>/etc/security/limits.conf
	fi
	if (($(ulimit -u)!=409600))
	then
		echo "* soft nproc 409600">>/etc/security/limits.d/20-nproc.conf
		echo "* hard nproc 409600">>/etc/security/limits.d/20-nproc.conf
	fi
}

main(){
	selinux
	firewall
	numa
	swap
	#io				#centos7默认就是deadline算法，可不调
	limits
}

main
