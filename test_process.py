#!/usr/bin/env python 

from serial import Serial, SerialException
from time import gmtime, strftime
import os
import traceback
import time 
import string

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
output = ""
targetOut = ""
refs = []
print "Monitoring test controller..."

while(testing):
	output += controller.read(controller.inWaiting())
	if(target.port): targetOut += target.read(target.inWaiting())
	if state == "start":
		if "start" in output:
			target.port = "/dev/ttyACM2"
			target.open()
			print "Target port : " + target.port
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
			controller.write("C18550F3000U_")
			entered = True
		if "ok" in output:
			state = "powering"
			entered = False
			print "Board Clamped."
			output = ""
	elif state == "powering":
		if not entered:
			print "Powering Board..."
			controller.write("W3H_")
			entered = True
		if "ok" in output:
			state = "fullstep"
			entered = False
			print "Target Board powered."
			output = ""
	elif state == "fullstep":
		if not entered:
			entered = True
			controller.write("M"+str(monitorTime)+"F100_")
			print "Testing steppers at full step..."
			target.write("U1_")
			target.write("C200F800U")
			target.write("C200F800D")
		if "ok" in output:
			state = "halfstep"
			entered = False
			print "Full Step test finished."
			print output
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
			print output
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
			print output
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
			print output
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
			state = "finished"
			entered = False
			print "Vrefs acquired"
			print output 
			output = ""
			targetOut = ""
	elif state == "mosfet high":
		if not entered:
			entered = True
			print "Testing Mosfets..."
			target.write("W9H")
			target.write("W8H")
			target.write("W7H")
			target.write("W6H")
			target.write("W3H")
			target.write("W2H")
		if targetOut.count("ok") == 6:
			controller.write("R44_")
			controller.write("R32_")
			controller.write("R45_")
			controller.write("R31_")
			controller.write("R46_")
			controller.write("R30_")
			targetOut = ""
		if output.count("ok") >= 6:
			target.write("W9L")
			target.write("W8L")
			target.write("W7L")
			target.write("W6L")
			target.write("W3L")
			target.write("W2L")
			print output
			output = ""
		if targetOut.count("ok") >= 6:
			controller.write("R44_")
			controller.write("R32_")
			controller.write("R45_")
			controller.write("R31_")
			controller.write("R46_")
			controller.write("R30_")
			targetOut = ""
		if output.count("ok") >= 6:
			print "Mosfets tested."
			print output
			output = ""
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
			print targetOut
			targetOut = ""
			entered = False
			state = "finished"
	elif state == "finished":
		print "Testing finished without errors."
		print "Powering off target"
		controller.write("W3L_")
		print "Preparing Test Jig for next board.."
		controller.write("H5000_")
		target.close()
		target.port = None
		state = "start"
