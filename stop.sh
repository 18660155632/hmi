#!/bin/bash

#关闭HMI应用

pids=($(ps aux | grep HMI | grep -v grep | awk '{print $2}'))

for pid in ${pids[@]}
do
	kill -9 ${pid};
done
