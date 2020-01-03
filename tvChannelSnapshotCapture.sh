#!/bin/sh

addrs=`seq 132 254`
mkdir -p snapshot

for a in $addrs
do 
	echo "=========================="
	echo "capture 233.50.201."$a
	echo "=========================="
	jpgFile=`printf %03d $a`
	ffmpeg -i http://192.168.119.101:8888/rtp/233.50.201.$a:5140 -ss 10 -f image2 -y ./snapshot/$jpgFile.jpg
done
