#!/usr/bin/env python 

from serial import Serial, SerialException
from time import gmtime, strftime
import os
import sys
import traceback
import time 
import string
import signal
import sys 
import subprocess 
import re
try:
	controller = Serial(port = "/dev/ttyACM0", baudrate = 115200)
	target = Serial(port = None, baudrate = 115200)
except SerialException:
	print "Error, could not connect"
	traceback.print_exc()
print "Target baudrate : " + str(target.baudrate)
print "Controller port : " + controller.name
print "Controller baudrate : " + str(controller.baudrate)


monitorTime = 1
stepperSpeed = 100
testing = True
state = "start"
entered = False
keyboard = ""
output = ""
targetOut = ""
refs = []
fullstepTest = []
halfstepTest = []
quarterstepTest = []
sixteenthstepTest = []
vrefTest = []
supplyTest = []
mosfethighTest = []
mosfetlowTest = []
thermistorTest = []

groupn = lambda l, n: zip(*(iter(l),) * n)

#Setup shutdown handlers
def signal_handler(signal, frame):
	print "Shutting down test server..."
	controller.close()
	target.close()
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

print "Test server started. Press CTRL-C to exit."
print "Monitoring test controller..."

while(testing):
	output += controller.read(controller.inWaiting())
	if(target.port): 
		targetOut += target.read(target.inWaiting())
	if state == "start":
		if "start" in output:
			state = "homing"
			print "Test started at " + strftime("%Y-%m-%d %H:%M:%S", gmtime())
			output = ""
			
	elif state == "homing":
		if not entered:
			print "Homing test jig..."
			controller.write("H5000_")
			entered = True
		if "ok" in output:
			state = "clamping"
			entered = False
			print "Homed."
			output = ""
	elif state == "clamping":
		if not entered:
			print "Clamping board..."
			controller.write("C18650F3000U_")
			entered = True
		if "ok" in output:
			state = "powering"
			entered = False
			print "Board Clamped."
			output = ""
	elif state == "uploading":
		print "Uploading Bootloader and setting fuses..."
		avr32u2 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158420', u'-patmega32u2', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX:i', u'-Uefuse:w:0xF4:m', u'-Uhfuse:w:0xD9:m', u'-Ulfuse:w:0xEF:m', u'-Ulock:w:0x0F:m'])
		avr32u2State = avr32u2.wait()
		print "atmega 32U2: "
		if avr32u2State == 0:
			print "Uploaded!"
			state = "connecting target"
		else:
			print "Upload Failed"
			state = "board fail"
		avr2560 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158597', u'-pm2560', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/stk500boot_v2_mega2560.hex:i', u'-Uefuse:w:0xFD:m', u'-Uhfuse:w:0xD0:m', u'-Ulfuse:w:0xFF:m', u'-Ulock:w:0x0F:m'])
		avr560State = avr2560.wait()
		print "atmega 2560: "
		if avr2560State == 0:
			print "Uploaded!"
			state = "connecting target"
		else:
			print "Upload Failed"
			state = "board fail"
			entered = False
	elif state == "program for test":
		print "Programming for the tests..."
		prog = subprocess.Popen("avrdude -patmega2560 -cstk500v2 -P/dev/ttyACM1 -b115200 -D -Uflash:w:/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex".split())
		state = prog.wait()
		if state == 0:
			print "Finished upload. Waiting for connection..."
			state = "connecting target"
			time.sleep(3)
		else:
			print "Upload failed"
			state = "board fail"
			entered = False
	elif state == "connecting target":
		print "Attempting connect..."	
		target.port = "/dev/ttyACM1"
		target.open()
		print "Target port : " + target.port 	
		state = "fullstep"	
	elif state == "powering":
		if not entered:
			print "Powering Board..."
			controller.write("W3H_")
			entered = True
		if "ok" in output:
			state = "program for test"
			entered = False
			print "Target Board powered."
			output = ""
			
	elif state == "fullstep":
		if not entered:
			entered = True
			print "Testing steppers at full step..."
			target.write("U1_")
			controller.write("M"+str(monitorTime)+"F100_")
			target.write("C200F800U")
			target.write("C200F800D")
		if "ok" in output:
			state = "halfstep"
			entered = False
			print "Full Step test finished."
			fullstepTest =groupn(map(int,re.findall(r'\b\d+\b', output)),10)
			print fullstepTest
			output = ""
	elif state == "halfstep":
		if not entered:
			entered = True
			controller.write("M"+str(monitorTime)+"F100_")
			print "Testing steppers at half step..."
			target.write("U2_")
			target.write("C400F1600U")
			target.write("C400F1600D")
		if "ok" in output:
			state = "quarterstep"
			entered = False
			print "Half Step test finished."
			halfstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),10)
			print halfstepTest
			output = ""
	elif state == "quarterstep":
		if not entered:
			entered = True
			controller.write("M"+str(monitorTime)+"F100_")
			print "Testing steppers at quarter step..."
			target.write("U4_")
			target.write("C800F3200U")
			target.write("C800F3200D")
		if "ok" in output:
			state = "sixteenthstep"
			entered = False
			print "Quarter Step test finished."
			quarterstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),10)
			print quarterstepTest
			output = ""
	elif state == "sixteenthstep":
		if not entered:
			entered = True
			controller.write("M"+str(monitorTime)+"F100_")
			print "Testing steppers at sixteenth step..."
			target.write("U16_")
			target.write("C3200F12800U")
			target.write("C3200F12800D")
		if "ok" in output:
			state = "vrefs"
			entered = False
			print "Sixteenth Step test finished."
			sixteenthTest = groupn(map(int,re.findall(r'\b\d+\b', output)),10)
			print sixteenthstepTest
			output = ""
	elif state == "vrefs":
		if not entered:
			entered = True
			controller.write("A8_") #x				
			controller.write("A6_") #y
			controller.write("A5_") #z
			controller.write("A4_") #e0
			controller.write("A3_") #e1
			print "Testing stepper driver references..."
		if output.count("ok") == 5:
			state = "supply test"
			entered = False
			print "Vrefs acquired"
			vrefTest = map(int,re.findall(r'\b\d+\b', output)) 
			print vrefTest	
			output = ""
			targetOut = ""
	elif state == "supply test":
		if not entered:
			entered = True
			controller.write("A7_") #extruder rail				
			controller.write("A2_") #bed rail
			print "Testing supply voltages..."
		if output.count("ok") == 2:
			state = "mosfet high"
			entered = False
			print "Voltages acquired."
			supplyTest = map(int,re.findall(r'\b\d+\b', output)) 
			print supplyTest	
			output = ""
			targetOut = ""
	elif state == "mosfet high":
		if not entered:
			entered = True
			print "Testing Mosfets High..."
			target.write("W9H")
			controller.write("R44_")
			target.write("W8H")
			controller.write("R32_")
			target.write("W7H")
			controller.write("R45_")
			target.write("W6H")
			controller.write("R31_")
			target.write("W3H")
			controller.write("R46_")
			target.write("W2H")
			controller.write("R30_")
		if output.count("ok") == 6:
			targetOut = ""
			print "Mosfet outputs recorded."
			mosfethighTest = map(int,re.findall(r'\b\d+\b', output)) 
			state = "mosfet low"
			print mosfethighTest
			output = ""
			targetOut = ""
			entered = False
	elif state == "mosfet low":
		if not entered:
			entered = True
			print "Testing mosfets Low..."
			controller.write("R44_")
			target.write("W8L")
			controller.write("R32_")
			target.write("W7L")
			controller.write("R45_")
			target.write("W6L")
			controller.write("R31_")
			target.write("W3L")
			controller.write("R46_")
			target.write("W2L")
			controller.write("R30_")
		if output.count("ok") >= 6:
			print "Mosfet outputs recorded."
			mosfetlowTest = map(int,re.findall(r'\b\d+\b', output)) 
			print mosfetlowTest
			output = ""
			targetOut = ""
			state = "thermistors"
			entered = False
	elif state == "thermistors":
		if not entered:
			entered = True
			print "Verifying thermistor readings..."
			target.write("A0_")
			target.write("A1_")
			target.write("A2_")
		if targetOut.count("ok") == 3:
			print "Readings acquired."
			thermistorTest = map(int,re.findall(r'\b\d+\b', targetOut)) 
			print thermistorTest
			targetOut = ""
			entered = False
			state = "program marlin"
	elif state == "program marlin":
		print "Disconnecting target from test script..."
		target.close()
		target.port = None 
		print "Programming Marlin..."
		prog = subprocess.Popen("avrdude -patmega2560 -cstk500v2 -P/dev/ttyACM1 -b115200 -D -Uflash:w:/home/ultimachine/workspace/johnnyr/Marlinth2.hex".split())
		state = prog.wait()
		if state == 0:
			print "Finished Marlin upload."
			state = "finished"
		else:
			print "Upload failed"
			state = "board fail"
			entered = False
	elif state == "finished":
		print "Testing finished without errors."
		print "Powering off target"
		controller.write("W3L_")
		print "Preparing Test Jig for next board.."
		controller.write("H5000_")
		state = "start"	
	elif state == "board fail":
		print "Board failed"
		target.close()
		target.port = None
		controller.write("W3L")
		controller.write("H5000_")
		state = "start"
		entered = False
