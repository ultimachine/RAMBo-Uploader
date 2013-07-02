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
import threading

print "RAMBo Test Server"

try:
	controller = Serial(port = "/dev/ttyACM0", baudrate = 115200)
	target = Serial(port = None, baudrate = 115200)
except SerialException:
	print "Error, could not connect"
	traceback.print_exc()
print "Target baudrate : " + str(target.baudrate)
print "Controller port : " + controller.name
print "Controller baudrate : " + str(controller.baudrate)
print "Waiting for controller initialization..."
controller.setDTR(0)
time.sleep(1)
controller.setDTR(1)
while not controller.inWaiting():
	time.sleep(0.1)

monitorPin = 44 #PL5 
triggerPin = 3 #bed
monitorFrequency = 1000
clampLength = 18550
targetPort = "/dev/ttyACM1"
testFwPath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
shipFwPath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
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

axisNames = ["X","Y","Z","E0","E1"]
thermistorNames = ["T0","T1","T2"]
supplyNames = ["Bed Rail","Extruder Rail"]

groupn = lambda lst, sz: [lst[i:i+sz] for i in range(0, len(lst), sz)]

#def analogToVoltage(reading, voltage = 5, bits = 10):
#	array = []
#	for reading /pow(2,10))*voltage

#Setup shutdown handlers
def signal_handler(signal, frame):
	print "Shutting down test server..."
	controller.write("W3L")
	controller.write("H5000")
	controller.close()
	target.close()
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

#Define test cases
def testVrefs(vals):
	for idx, val in enumerate(vals):
		if not 170 <= val <= 195:
			global state
			state = "board fail"
			print axisNames[idx] + " axis vref incorrect"
			return False
	if max(vals) - min(vals) >= 15:
		print "Value variance too high!"
		global state
		state = "board fail"
		return False
	return True 

def testSupply(vals):
	for idx, val in enumerate(vals):
		if not 210 <= val <= 220:
			global state
			state = "board fail"
			print "Test " + supplyNames[idx] + " supply"
			return False
	return True

def testThermistor(vals):
	for idx, val in enumerate(vals):
		if not 975 <= val <= 985:
			global state
			state = "board fail"
			print "Check Thermistor " + thermistorNames[idx]
			return False
	return True

def testMosfetLow(vals):
	for idx, val in enumerate(vals):
		if not val == 1:
			global state
			state = "board fail"
			print "Check MOSFET " + str(idx)
			return False
	return True

def testMosfetHigh(vals):
	for idx, val in enumerate(vals):
		if not val == 0:
			global state
			state = "board fail"
			print "Check MOSFET " + str(idx)
			return False
	return True

def testStepperResults(vals):
	for i in range(5):
		forward = vals[i]
		reverse = vals[i+5]
		print "Forward -> " + str(forward) + "Reverse -> " + str(reverse)
		for j in range(5):
			if forward[j] in range(reverse[4-j]-10,reverse[4-j]+10):
				pass
			else: 
				global state
				state = "board fail"
				print "Check "+axisNames[i]+" stepper"
				return False
	print "Test passed."
	return True	

print "Test server started. Press CTRL-C to exit."
print "Monitoring test controller..."

while(testing):
	output += controller.read(controller.inWaiting())
	#raw_input("Press Enter to continue...")
	if(target.port): 
		targetOut += target.read(target.inWaiting())
	if state == "start":
		if "start" in output:
			state = "clamping"
			print "Test started at " + strftime("%Y-%m-%d %H:%M:%S", gmtime())
			output = ""
			targetOut = ""
	elif state == "clamping":
		print "Clamping test jig..."
		controller.write("H5000_")
		controller.write("C"+str(clampLength)+"F3000U_")
		state = "program for test"
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
		print "Detecting target..."
		while not os.path.exists(targetPort):
			time.sleep(0.5)
		print "Programming for the tests..."
		command = "avrdude -F -patmega2560 -cstk500v2 -P"+targetPort+" -b115200 -D -Uflash:w:"+testFwPath
		prog = subprocess.Popen(command.split())
		print "Avrdude pid... " + str(prog.pid)
		state = prog.wait()
		if state == 0:
			print "Finished upload. Waiting for connection..."
			state = "connecting target"
			while not os.path.exists(targetPort):
				time.sleep(0.5)
		else:
			print "Upload failed"
			state = "board fail"
			entered = False
	elif state == "connecting target":
		print "Attempting connect..."	
		target.port = targetPort
		target.open()
		while not target.inWaiting():
			pass
		print "Target port : " + target.port 	
		state = "powering"
		targetOut = ""
	elif state == "powering":
		if not entered:
			print "Waiting for homing to complete"
			while not output.count("ok") == 2:
				output += controller.read(controller.inWaiting())
			output = ""
			print "Powering Board..."
			controller.write("W3H_")
			entered = True
		if "ok" in output:
			state = "thermistors"
			entered = False
			print "Target Board powered."
			output = ""
			targetOut = ""
	elif state == "fullstep":
		if not entered:
			entered = True
			print "Testing steppers at full step..."
			target.write("U1_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C200F800UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output+="ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C200F800DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Full Step test finished."
			fullstepTest =groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			if testStepperResults(fullstepTest):
				state = "halfstep"
			output = ""
			fullstepTest = []
	elif state == "halfstep":
		if not entered:
			entered = True
			print "Testing steppers at half step..."
			target.write("U2_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C400F1600UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output+="ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C400F1600DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Half Step test finished."
			halfstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			if testStepperResults(halfstepTest):
				state = "quarterstep"
			output = ""
			halfstepTest = []
	elif state == "quarterstep":
		if not entered:
			entered = True
			print "Testing steppers at quarter step..."
			target.write("U4_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C800F3200UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output +="ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C800F3200DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Quarter Step test finished."
			quarterstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			if testStepperResults(quarterstepTest):
				state = "sixteenthstep"
			output = ""
			quarterstepTest = []
	elif state == "sixteenthstep":
		if not entered:
			entered = True
			print "Testing steppers at sixteenth step..."
			target.write("U16_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C3200F12800UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output += "ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C3200F12800DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Sixteenth Step test finished."
			sixteenthstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			if testStepperResults(sixteenthstepTest):
				state = "program marlin"
			output = ""
			sixteenthstepTest = []
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
			entered = False
			print "Vref values..."
			vrefTest = map(int,re.findall(r'\b\d+\b', output)) 
			print vrefTest
			if testVrefs(vrefTest):
				state = "fullstep"
			output = ""
			targetOut = ""
	elif state == "supply test":
		if not entered:
			entered = True
			controller.write("A7_") #extruder rail				
			controller.write("A2_") #bed rail
			print "Testing supply voltages..."
		if output.count("ok") == 2:
			entered = False
			print "Supply voltage values..."
			supplyTest = map(int,re.findall(r'\b\d+\b', output)) 
			print supplyTest	
			if testSupply(supplyTest):
				state = "mosfet high"
			output = ""
			targetOut = ""
	elif state == "mosfet high":
		if not entered:
			entered = True
			print "Testing Mosfets High..."
			target.write("W9H")
			target.write("W8H")
			target.write("W7H")
			target.write("W6H")
			target.write("W3H")
			target.write("W2H")
			time.sleep(0.1)
			controller.write("Q44_")
			controller.write("Q32_")
			controller.write("Q45_")
			controller.write("Q31_")
			controller.write("Q46_")
			controller.write("Q30_")
		if output.count("ok") == 6:
			entered = False
			print "Mosfet output values..."
			mosfethighTest = map(int,re.findall(r'\b\d+\b', output)) 
			print mosfethighTest
			if testMosfetHigh(mosfethighTest):
				state = "mosfet low"
			output = ""
			targetOut = ""
	elif state == "mosfet low":
		if not entered:
			entered = True
			print "Testing mosfets Low..."
			target.write("W9L")
			target.write("W8L")
			target.write("W7L")
			target.write("W6L")
			target.write("W3L")
			target.write("W2L")
			time.sleep(0.1)
			controller.write("Q44_")
			controller.write("Q32_")
			controller.write("Q45_")
			controller.write("Q31_")
			controller.write("Q46_")
			controller.write("Q30_")
		if output.count("ok") == 6:
			entered = False
			print "Mosfet output values..."
			mosfetlowTest = map(int,re.findall(r'\b\d+\b', output)) 
			print mosfetlowTest
			if testMosfetLow(mosfetlowTest):
				state = "vrefs"
			output = ""
			targetOut = ""
	elif state == "thermistors":
		if not entered:
			entered = True
			print "Verifying thermistor readings..."
			target.write("A0_")
			target.write("A1_")
			target.write("A2_")
		if targetOut.count("ok") == 3:
			print "Target thermistor readings..."
			thermistorTest = map(int,re.findall(r'\b\d+\b', targetOut)) 
			print thermistorTest
			if testThermistor(thermistorTest):
				state = "supply test"
			targetOut = ""
			entered = False
	elif state == "program marlin":
		print "Disconnecting target from test script..."
		target.flushInput()
		target.flushOutput()
		target.close()
		target.port = None 
		print "Programming Marlin..."
		command = "avrdude -patmega2560 -cstk500v2 -P"+targetPort+" -b115200 -D -Uflash:w:"+shipFwPath
		prog = subprocess.Popen(command.split())
		print "avrdude pid... " + str(prog.pid)
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

