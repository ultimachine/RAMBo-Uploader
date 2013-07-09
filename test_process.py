#!/usr/bin/env python 

from serial import Serial, SerialException
from time import gmtime, strftime
from termcolor import colored
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
import argparse
import avrdude
import atmega

print "RAMBo Test Server"

try:
	controller = Serial(port = "/dev/ttyACM1", baudrate = 115200)
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

timeout = {'count': 0, 'state': False, 'time': 5} # dictionary to organize timeout values

while not controller.inWaiting():
	time.sleep(0.1)
	timeout.count += 0.1
	if timeout.count >= timeout.time: #5 second timeout
		timeout.state = True
		print "Could not connect to Test Controller, try hitting reset while \
               waiting for initialization..."
		controller.close()
		sys.exit(0)

        
monitorPin = 44 #PL5 
triggerPin = 3 #bed
monitorFrequency = 1000
clampLength = 18550
targetPort = "/dev/ttyACM2"
testFirmwarePath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
stepperSpeed = 100
testing = True
state = "start"
entered = False
errors = ""
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
supplyNames = ["Extruder Rail","Bed Rail"]

groupn = lambda lst, sz: [lst[i:i+sz] for i in range(0, len(lst), sz)]

#def analogToVoltage(reading, voltage = 5, bits = 10):
#	array = []
#	for reading /pow(2,10))*voltage

#Setup target test firmware object to pass to AVRDUDE.
testFirmware = Atmega()
testFirmware.name = "atmega2560"
testFirmware.bootloader = testFirmwarePath

#Setup target vendor firmware object to pass to AVRDUDE. 
vendorFirmware = Atmega()
vendorFirmware.name = "atmega2560"
vendorFirmware.bootloader = vendorFirmwarePath

#Setup up avrdude config for upload to an Arduino.
avrdude = Avrdude()
avrdude.path = "/usr/bin/avrdude"
avrdude.programmer = "stk200v2"
avrdude.port = targetPort
avrdude.baudrate = 115200
avrdude.autoEraseFlash = True

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
	global errors
	for idx, val in enumerate(vals):
		if not 170 <= val <= 195:
			errors += colored(axisNames[idx] + " axis vref incorrect\n", 'red')
			return False
	if max(vals) - min(vals) >= 15:
		errors +=  colored("Vref variance too high!\n",'red')
		return False
	return True 

def testSupply(vals):
	global errors
	for idx, val in enumerate(vals):
		if not 210 <= val <= 220:
			errors += colored("Test " + supplyNames[idx] + " supply\n", 'red')
			return False
	return True

def testThermistor(vals):
	global errors
	for idx, val in enumerate(vals):
		if not 975 <= val <= 985:
			errors += colored("Check Thermistor" + thermistorNames[idx] + "\n", 'red')
			return False
	return True

def testMosfetLow(vals):
	global errors
	for idx, val in enumerate(vals):
		if not val == 1:
			errors += colored("Check MOSFET " + str(idx) + "\n", 'red')
			return False
	return True

def testMosfetHigh(vals):
	global errors
	for idx, val in enumerate(vals):
		if not val == 0:
			errors += colored("Check MOSFET " + str(idx) + "\n", 'red')
			return False
	return True

def testStepperResults(vals):
	global errors
	for i in range(5):
		forward = vals[i]
		reverse = vals[i+5]
		print "Forward -> " + str(forward) + "Reverse -> " + str(reverse)
		for j in range(5):
			if forward[j] in range(reverse[4-j]-10,reverse[4-j]+10):
				pass
			else: 
				errors += colored("Check "+axisNames[i]+" stepper\n", 'red')
				return False
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
			
		print "Programming target with test firmware..."
		finishedUpload = avrdude.upload(testFirmware, timeout = 25)
		
		if finishedUpload:
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
			state = "halfstep"
			output = ""

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
			state = "quarterstep"
			output = ""

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
			state = "sixteenthstep"
			output = ""

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
			state = "program marlin"
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
			entered = False
			vrefTest = map(int,re.findall(r'\b\d+\b', output)) 
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
			supplyTest = map(int,re.findall(r'\b\d+\b', output)) 
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
			mosfethighTest = map(int,re.findall(r'\b\d+\b', output)) 
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
			mosfetlowTest = map(int,re.findall(r'\b\d+\b', output)) 
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
			thermistorTest = map(int,re.findall(r'\b\d+\b', targetOut)) 
			state = "supply test"
			targetOut = ""
			entered = False

	elif state == "program marlin":
		print "Disconnecting target from test script..."
		target.flushInput()
		target.flushOutput()
		target.close()
		target.port = None 
		print "Programming target with vendor firmware..."
		finishedUpload = avrdude.upload(vendorFirmware, timeout = 30)
		if finishedUpload:
			print "Finished Marlin upload."
			state = "processing"
		else:
			print "Upload failed"
			state = "board fail"
			entered = False

	elif state == "processing":
		passed = True
		print "Supply voltage values..."
		print supplyTest	
		passed &= testSupply(supplyTest)	

		print "Vref values..."
		print vrefTest
		passed &= testVrefs(vrefTest)

		print "Target thermistor readings..."
		print thermistorTest
		passed &= testThermistor(thermistorTest)

		print "Mosfet high values..."
		print mosfethighTest
		passed &= testMosfetHigh(mosfethighTest)

		print "Mosfet low values..."
		print mosfetlowTest
		passed &= testMosfetLow(mosfetlowTest)

		print "Full step results"
		passed &= testStepperResults(fullstepTest)

		print "Half step results"
		passed &= testStepperResults(halfstepTest)

		print "Quarter step results"
		passed &= testStepperResults(quarterstepTest)

		print "Sixteeth step results"
		passed &= testStepperResults(sixteenthstepTest)
		
		print errors
		
		if not passed:
			print colored("Board failed",'red')
		else:
			print colored("Board passed",'green')
		state = "finished"
		errors = ""
	elif state == "finished":
		print "Preparing Test Jig for next board..."
		controller.write("W3L_")
		controller.write("H5000_")
		state = "start"	

