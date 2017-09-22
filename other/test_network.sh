#! /bin/bash

#log = /home/pi/wjc/network.log

#if [ ! -f ${log} ]
#then
#	touch ${log}
#fi

ping -c 1 192.168.1.1 > /dev/null 2>&1
if [ $? -eq 0 ]; then
	echo "network is ok" 
else
	echo "network is wrong" 
fi
