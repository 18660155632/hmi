#!/bin/bash

#启动HMI应用

source /opt/HMI/venv/bin/activate 
#nohup uvicorn mysql_install_app.main:app --host=172.16.3.140 --port=8008 --reload & disown 
uvicorn mysql_install_app.main:app --host=172.16.3.140 --port=8008 --reload
