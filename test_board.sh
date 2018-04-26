#!/bin/bash
cd ~/workspace/RAMBo-Uploader
while :
do
	./test_process.py 1 $1
        echo ------------
        echo --  TEST PROGRAM CRASHED - UNDO PREVOUS ACTIONS AND PRESS ENTER TO RESTART
        echo --  this might be caused by bridge on usb. unclamp fixture or remove usb.
        echo -----------
        read
	sleep 1
done
