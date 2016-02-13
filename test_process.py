#!/usr/bin/env python 

from __future__ import division
from serial import Serial, SerialException
import time
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
from testprocessor import *
from avrdude import *
from atmega import *
from testinterface import *
import psycopg2
from subprocess import call
import shlex

print "RAMBo Test Server"
directory = os.path.split(os.path.realpath(__file__))[0]
version = subprocess.check_output(['git', '--git-dir='+directory+'/.git',
                                   'rev-parse', 'HEAD'])
version = version.strip()
print "Git version - " + str(version)

gitdiff = subprocess.Popen( shlex.split('/usr/bin/git --git-dir='+directory+'/.git diff --exit-code --quiet') ).wait()
gitbranch = subprocess.check_output(shlex.split('/usr/bin/git --git-dir='+directory+'/.git rev-parse --abbrev-ref HEAD'))

print "Connecting to database..."
# Open our file outside of git repo which has database location, password, etc
dbfile = open(directory+'/postgres_info.txt', 'r')
postgresInfo = dbfile.read()
dbfile.close()
try:
    testStorage = psycopg2.connect(postgresInfo)
except:
    print "Could not connect!"
    sys.exit(0)

#Configuration
monitorPin = 44 #PL5 on test controller
triggerPin = 3 #bed on target board
powerPin = 3 #bed on test controller
homingRate = 8000 #5000
clampingRate = 7000 #4000
# clamping length for : 1.1=18550, 1.2=16000
#clampingLength = 18550
#clampingLength = 16300
clampingLength = 16000 #16200
monitorFrequency = 1000
stepperTestRPS = 5 #3 #rotations per second for the stepper test
#controllerPort = "/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_64033353730351918201-if00"
controllerPort = "/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_64037323235351607090-if00"
targetPort = "/dev/ttyACM1"
testFirmwarePath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
testing = True
state = "start"
serialNumber = ""
vrefPins = [8, 6, 5, 4, 3] #x, y, z, e0, e1 on controller
supplyPins = [7, 2, 0] #extruder rail, bed rail, 5v rail on controller
mosfetOutPins = [9, 8, 7, 6, 3, 2] #On target
mosfetInPins = [44, 32, 45, 31, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
endstopOutPins = [83, 82, 81, 80, 79, 78]
endstopInPins = [12, 11, 10, 24, 23, 30]
thermistorPins = [0, 1, 2, 7]
logFile = '/home/ultimachine/tplog.txt'
testjig = "rambo" #used to tell state machine if it needs to clamp or not

relayBedMotorsPin = 4
relayBedPin = 4
relayLogicPin = 5
relayMotorsPin = 2

waveOperator = None
qcPerson = None
testPerson = None

overCurrentChecking = True
currentReadings = []

#set target COM port from first command line argument
if len(sys.argv) >= 2:
    targetPort = "/dev/ttyACM" + sys.argv[1]
    print "targetPort: " + targetPort

def set_minirambo_configs():
    global triggerPin
    global testFirmwarePath
    global vendorFirmwarePath
    global vrefPins
    global mosfetOutPins
    global mosfetInPins
    global thermistorPins
    global testjig
    global testProcessor
    triggerPin = 4
    testFirmwarePath = "/home/ultimachine/workspace/MiniRamboTestJigFirmware/target_test_firmware.hex"
    vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Mini-Rambo-Marlin/Marlin.cpp.hex"
    vrefPins = [8, 5, 4,] #x, y, z, e0, e1 on controller
    mosfetOutPins = [3, 6, 8, 4] #On target
    mosfetInPins = [44, 45, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
    thermistorPins = [0, 1, 2]
    testjig = "minirambo"

    testProcessor = miniRamboTestProcessor

    #update variables to the Atmega class instances
    testFirmware.bootloader = testFirmwarePath
    vendorFirmware.bootloader = vendorFirmwarePath
    print "Testjig is now : " + testjig

def set_rambo_configs():
    global triggerPin
    global testFirmwarePath
    global vendorFirmwarePath
    global vrefPins
    global mosfetOutPins
    global mosfetInPins
    global thermistorPins
    global testjig
    global testProcessor
    triggerPin = 3 
    testFirmwarePath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
    vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
    vrefPins = [8, 6, 5, 4, 3] #x, y, z, e0, e1 on controller
    mosfetOutPins = [9, 8, 7, 6, 3, 2] #On target
    mosfetInPins = [44, 32, 45, 31, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
    thermistorPins = [0, 1, 2, 7]
    testjig = "rambo"

    testProcessor = ramboTestProcessor

    testFirmware.bootloader = testFirmwarePath
    vendorFirmware.bootloader = vendorFirmwarePath
    print "Testjig is now : " + testjig

#Setup test interfaces
controller = TestInterface()
target = TestInterface()
if not controller.open(port = controllerPort):
    print "Check controller connection."
    sys.exit(0)
    
#Setup target test firmware object to pass to AVRDUDE.
testFirmware = Atmega()
testFirmware.name = "atmega2560"
testFirmware.bootloader = testFirmwarePath

MRtestFirmware = Atmega()
MRtestFirmware.name = "atmega2560"
MRtestFirmware.bootloader = "/home/ultimachine/workspace/MiniRamboTestJigFirmware/target_test_firmware.hex"


#Setup target vendor firmware object to pass to AVRDUDE. 
vendorFirmware = Atmega()
vendorFirmware.name = "atmega2560"
vendorFirmware.bootloader = vendorFirmwarePath

#Setup up avrdude config for upload to an Arduino.
avrdude = Avrdude()
avrdude.path = "/usr/bin/avrdude"
avrdude.programmer = "stk500v2"
avrdude.port = targetPort
avrdude.baudrate = "115200"
avrdude.autoEraseFlash = True

#Define our test processor
miniRamboTestProcessor = TestProcessor()
miniRamboTestProcessor.axisNames = ["X","Y","Z","E0"] #no E1
miniRamboTestProcessor.vrefNames = ["X,Y","Z","E0"]
miniRamboTestProcessor.thermistorNames = ["T0","T1","T2"] #no T3
miniRamboTestProcessor.mosfetNames = ["Bed","Fan1","Fan0","Heat0"]
miniRamboTestProcessor.thermistorLow = 925
miniRamboTestProcessor.thermistorHigh = 955
ramboTestProcessor = TestProcessor()
testProcessor = ramboTestProcessor

#Check for command line parameter override of test jig
if len(sys.argv) >= 3:
    if sys.argv[2] == "rambo":
        set_rambo_configs()
    if sys.argv[2] == "minirambo":
        set_minirambo_configs()

#Setup shutdown handlers
def signal_handler(signal, frame):
    print "Shutting down test server..."
    powerOff()
    controller.home(homingRate, wait = False)
    controller.close()
    target.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

print "Test server started. Press CTRL-C to exit."
print "Monitoring test controller..."

def analog2volt(readings=[], voltage = 5, bits = 10, dividerFactor = 0.088):
        #divider factor is R2/(R1+R2)
        #return (val/pow(2, bits))*(voltage/dividerFactor)
	#return ((val/1024) * (5.0/0.088))
        voltages = []
        #divider factor is R2/(R1+R2)
        for val in readings:
            voltages += [(val/pow(2, bits))*(voltage/dividerFactor)]
	return voltages

def showSupplys():
                 supplyVoltagesUnpowered = []

		 time.sleep(0.1)
                 for pin in supplyPins:
                     supplyVoltagesUnpowered += analog2volt(controller.analogRead(pin))
                 print supplyVoltagesUnpowered

def clamp():
                 #controller.home(rate = 4000, wait = False)
                 #controller.runSteppers(frequency = 4000, steps = 300,direction = controller.UP, wait = False)
                 controller.home(rate = homingRate, wait = False)
                 controller.runSteppers(frequency = clampingRate, steps = clampingLength,direction = controller.UP, wait = False)
                 if controller.waitForFinish(commands = 2, timeout = 30, clear = True):
                     print "Wait worked!"
                 else:
                     print "Wait timed out!"
def home():
                 print "Homing!!!!!!!"
                 controller.home(rate = homingRate, wait = True)
                 controller.runSteppers(frequency = clampingRate, steps = 300,direction = controller.UP, wait = False)
def powerOn():
                 controller.pinHigh(powerPin)
                 controller.pinHigh(relayBedMotorsPin)
                 return controller.pinHigh(relayLogicPin)
def powerOff():
                 controller.pinLow(powerPin)
                 controller.pinLow(relayBedMotorsPin)
                 controller.pinLow(relayLogicPin)

def isOverCurrent(threshold = 0.02):
                 global testProcessor
                 adcReadings = []

                 time.sleep(0.1)
                 for count in range(5):
                      controller.analogRead(1)
                 for count in range(20):
                      adcReadings += controller.analogRead(1)
                 meanAmps = round(sum(adcReadings)/len(adcReadings) * (5.0/1024.0),4)
                 print colored("current_reading: " + str(meanAmps) + " Amps",'blue')
                 currentReadings.append(meanAmps)
                 if not overCurrentChecking: 
                     return False

                 if(meanAmps > threshold):
                     powerOff()
                     testProcessor.errors += "Over " + str(threshold) + " amps\n"
                     print colored("Board is OVER MAXIMUM current threshold: " + str(threshold),'red')
                     print colored("Check for reverse capacitor or short circuit...",'yellow')
                     return True
                 return False

def isOverCurrentBedMotors():
                  controller.pinHigh(relayBedMotorsPin)
                  return isOverCurrent(threshold = 0.0)


def isOverCurrentLogic():
                  controller.pinLow(relayBedMotorsPin)
                  controller.pinHigh(relayLogicPin)
                  return isOverCurrent(threshold = 0.2)

def targetMotorsDisable():
                 ramboMotorEnablePins = [29,28,27,26,25]
                 for enablePin in ramboMotorEnablePins:
                      target.pinHigh(enablePin)

while(testing):
    if state == "start":
	failCode = None
	failNote = None
        currentReadings = []

        while True:
            print "Enter serial number : "
            serialNumber = raw_input().strip()
            if serialNumber == "m":
                 set_minirambo_configs()
                 continue
            if serialNumber == "r":
                 set_rambo_configs()
                 continue
            if serialNumber == "p":
                 print "Powering!!!!!!!"
                 powerOn()
                 continue
            if serialNumber == "o":
                 print "Removing Power!!!!!!!"
                 powerOff()
                 continue
            if serialNumber == "c":
                 print "Clamping!!!!!!!"
                 controller.home(rate = homingRate, wait = False)
                 controller.runSteppers(frequency = clampingRate, steps = clampingLength,direction = controller.UP, wait = False)
                 continue
            if serialNumber == "h":
                 home()
                 continue
            if serialNumber == "s":
                 print "Supply Test!!!!!!!"
                 supplyVoltagesUnpowered = []
                 for pin in supplyPins:
                     supplyVoltagesUnpowered += analog2volt(controller.analogRead(pin))
                 print supplyVoltagesUnpowered
                 continue
            if serialNumber == "a":
                 for count in range(5):
                      controller.analogRead(1)
                 ampreadings=[]
                 for count in range(20):
                      ampreadings += controller.analogRead(1)
                 amps = sum(ampreadings)/len(ampreadings) * (5.0/1024.0)
                 print "current_reading: " + str(amps) + " Amps"
                 continue
            if serialNumber == "bedon":
                 controller.pinHigh(relayBedPin)
                 continue
            if serialNumber == "bedoff":
                 controller.pinLow(relayBedPin)
                 continue
            if serialNumber == "logon":
                 controller.pinHigh(relayLogicPin)
                 continue
            if serialNumber == "logoff":
                 controller.pinLow(relayLogicPin)
                 continue
            if serialNumber == "moton":
                 controller.pinHigh(relayMotorsPin)
                 continue
            if serialNumber == "motoff":
                 controller.pinLow(relayMotorsPin)
                 continue
            if serialNumber == "j":
                 powerOn()
                 isOverCurrent()
                 time.sleep(0.5)
                 isOverCurrent()
                 powerOff()
                 continue
            if serialNumber == "ocon":
                 overCurrentChecking = True
                 continue
            if serialNumber == "ocoff":
                 overCurrentChecking = False
                 continue
            if serialNumber == "open":
                 target.open(port = targetPort)
                 continue
            if serialNumber == "close":
                 target.close()
                 continue
            if serialNumber == "moton":
                 ramboMotorEnablePins = [29,28,27,26,25]
                 for enablePin in ramboMotorEnablePins:
                      target.pinLow(enablePin)
                 continue
            if serialNumber == "motoff":
                 ramboMotorEnablePins = [29,28,27,26,25]
                 for enablePin in ramboMotorEnablePins:
                      target.pinHigh(enablePin)
                 continue
            if serialNumber == "motoffamps":
                 powerOn()
                 target.open(port = targetPort)

                 ramboMotorEnablePins = [29,28,27,26,25]
                 for enablePin in ramboMotorEnablePins:
                      target.pinLow(enablePin)
                 time.sleep(1)
                 ramboMotorEnablePins = [29,28,27,26,25]
                 for enablePin in ramboMotorEnablePins:
                      target.pinHigh(enablePin)
                 time.sleep(0.5)
                 isOverCurrent()
                 time.sleep(3)
                 isOverCurrent()
                 powerOff()
                 continue
            if serialNumber == "qc":
                 print "Enter Quality Control person initials: "
                 qcPerson = raw_input().strip()
                 continue
            if serialNumber == "wave":
                 print "Enter Wave Operator initials: "
                 waveOperator = raw_input().strip()
                 continue
            if serialNumber == "tester":
                 print "Enter Test Operator initials: "
                 testPerson = raw_input().strip()
                 continue
            if serialNumber == "ps":
                 print "Supply Test!!!!!!!"
                 clamp()
                 powerOn()
                 showSupplys()
                 showSupplys()
                 powerOff()
                 showSupplys()
                 showSupplys()

                 for secs in range(10):
                     print "seconds: " + str(secs)
                     time.sleep(1)
                     showSupplys()
                     showSupplys()
                 home()
                 continue

            if serialNumber == "grr":
                 print "Test analog2volt"
                 print "Test: " + str(analog2volt(216))
                 continue

            if serialNumber == "fw":
                 print "Uploading Test Firmware!!!!!!!"
                 avrdude.upload(testFirmware, timeout = 10)
                 continue

            try: 
                sNum = int(serialNumber)
                if(  (sNum in range(10000000,10099000))  or  (sNum in range(55500000,55555555)) ): 
                    break
                else:
                    print "Invalid Entry. (Use 55500000-55555555 for Testing)."
                    call(["beep","-f 2250"])
            except: 
                print "Error!  That was not a valid entry. Try again... (Use 55500000-55555555 for Testing)"
                call(["beep","-f 2250"])

        print "Testjig is now: " + testjig
        print "VendorFirmware:" + vendorFirmwarePath

	#call(["cat", "~/tplog.txt | grep " + serialNumber])
	call(["./tpgrep.sh",serialNumber])
        with open(logFile, "a") as tpLog:
            tpLog.write(serialNumber + '\n') 

        if testjig == "rambo":
            print "Press button to begin test"
            controller.waitForStart() #Blocks until button pressed
            state = "clamping"
        if testjig == "minirambo":
            state = "powering"
        print "Test started at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    elif state == "clamping":
        print "Clamping test jig..."
        controller.home(rate = homingRate, wait = False)
        controller.runSteppers(frequency = clampingRate, steps = clampingLength,
                               direction = controller.UP, wait = False)
        state = "wait for homing"
#        state = "program for test"

    elif state == "uploading":
        print "Uploading Bootloader and setting fuses..."
        avr32u2 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158420', u'-patmega32u2', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX:i', u'-Uefuse:w:0xF4:m', u'-Uhfuse:w:0xD9:m', u'-Ulfuse:w:0xEF:m', u'-Ulock:w:0x0F:m'])
        avr2560 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158597', u'-pm2560', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/stk500boot_v2_mega2560.hex:i', u'-Uefuse:w:0xFD:m', u'-Uhfuse:w:0xD0:m', u'-Ulfuse:w:0xFF:m', u'-Ulock:w:0x0F:m'])

    elif state == "program for test":
        print "Programming target with test firmware..."
        if avrdude.upload(testFirmware, timeout = 10):
            state = "connecting target"
        else:
            print "Upload failed."
            state = "board fail"

    elif state == "connecting target":
        print "Attempting connect..."   
        if target.open(port = targetPort):
            state = "mosfet high"
#            state = "wait for homing"
        else:
            print "Connect failed."
            state = "board fail"

    elif state == "wait for homing":
        print "Waiting for homing to complete..."
        if controller.waitForFinish(commands = 2, timeout = 10, clear = True):
            state = "powering"
        else:
            print "Homing failed."
            state = "board fail"
            
    elif state == "powering":   
        print "Powering Board..."
        if isOverCurrentBedMotors():
            state = "board fail"
        elif isOverCurrentLogic():
            state = "board fail"
        elif powerOn():
            time.sleep(0.2)
            if isOverCurrent(): 
                state = "board fail"
            else:
                state = "supply test"
        else:
            print "Powering failed."
            state = "board fail"
            
    elif state == "fullstep":
        print "Testing full step forward..."
        target.setMicroStepping(1)
        target.runSteppers(frequency = 200*stepperTestRPS, steps = 200, 
                           direction = target.UP, triggerPin = triggerPin, wait = False)
        testProcessor.fullStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing full step reverse..."
        target.runSteppers(frequency = 200*stepperTestRPS, steps = 200, 
                           direction = target.DOWN, triggerPin = triggerPin, wait = False)
        testProcessor.fullStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        finished = target.waitForFinish(commands = 2, timeout = 2, clear = True)
        if -1 in testProcessor.fullStep or not finished:
            print "Monitoring failed."
            state = "board fail"
        else:    
            state = "halfstep"

    elif state == "halfstep":
        print "Testing half step forward..."
        target.setMicroStepping(2)
        target.runSteppers(frequency = 400*stepperTestRPS, steps = 400, 
                           direction = target.UP, triggerPin = triggerPin, wait = False)
        testProcessor.halfStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing half step reverse..."
        target.runSteppers(frequency = 400*stepperTestRPS, steps = 400, 
                           direction = target.DOWN, triggerPin = triggerPin, wait = False)
        testProcessor.halfStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        finished = target.waitForFinish(commands = 2, timeout = 2, clear = True)
        if  -1 in testProcessor.halfStep or not finished:
            print "Monitoring failed."
            state = "board fail"
        else:    
            state = "quarterstep"

    elif state == "quarterstep":
        print "Testing quarter step forward..."
        target.setMicroStepping(4)
        target.runSteppers(frequency = 800*stepperTestRPS, steps = 800, 
                           direction = target.UP, triggerPin = triggerPin, wait = False)
        testProcessor.quarterStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing quarter step reverse..."
        target.runSteppers(frequency = 800*stepperTestRPS, steps = 800, 
                           direction = target.DOWN, triggerPin = triggerPin, wait = False)
        testProcessor.quarterStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        finished = target.waitForFinish(commands = 2, timeout = 2, clear = True)
        if -1 in testProcessor.quarterStep or not finished:
            print "Monitoring failed."
            state = "board fail"
        else:    
            state = "sixteenthstep"

    elif state == "sixteenthstep":
        print "Testing sixteeth step forward..."
        target.setMicroStepping(16)
        target.runSteppers(frequency = 3200*stepperTestRPS, steps = 3200, 
                           direction = target.UP, triggerPin = triggerPin, wait = False)
        testProcessor.sixteenthStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing sixteeth step reverse..."
        target.runSteppers(frequency = 3200*stepperTestRPS, steps = 3200, 
                           direction = target.DOWN, triggerPin = triggerPin, wait = False)
        testProcessor.sixteenthStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        finished = target.waitForFinish(commands = 2, timeout = 2, clear = True)
        if -1 in testProcessor.sixteenthStep or not finished:
            print "Monitoring failed."
            state = "board fail"
        else:    
            state = "thermistors"

    elif state == "vrefs":
        print "Testing stepper driver references..."
        for pin in vrefPins:
            testProcessor.vrefs += controller.analogRead(pin)
        if -1 in testProcessor.vrefs:
            print "Reading references failed."
            state = "board fail"
        else:     
            state = "fullstep"
#            state = "thermistors"
#            state = "processing"

    elif state == "supply test":
        print "Testing supply voltages..."
        for pin in supplyPins:
            testProcessor.supplys += controller.analogRead(pin)
        if -1 in testProcessor.supplys:
            print "Reading supplies failed."
            state = "board fail"
        else:     
            state = "program for test" 
 
    elif state == "mosfet high":
        passed = True
        print "Testing MOSFETs high..."
        for pin in mosfetOutPins:
            passed &= target.pinHigh(pin)
        for pin in mosfetInPins:
            testProcessor.mosfetHigh += controller.pullupReadPin(pin)
        if -1 in testProcessor.mosfetHigh or not passed:
            print "Reading mosfets failed."
            state = "board fail"      
        else:     
            state = "mosfet low"

    elif state == "mosfet low":
        passed = True
        print "Testing MOSFETs low..."
        for pin in mosfetOutPins:
            passed &= target.pinLow(pin)
        for pin in mosfetInPins:
            testProcessor.mosfetLow += controller.pullupReadPin(pin)
        if -1 in testProcessor.mosfetLow or not passed:
            print "Reading mosfets failed."
            state = "board fail"      
        else:     
            state = "endstop high"

    elif state == "endstop high":
        passed = True
        print "Testing endstops high..."
        for pin in endstopOutPins:
            passed &= controller.pinHigh(pin)
        for pin in endstopInPins:
            testProcessor.endstopHigh += target.readPin(pin)
        if -1 in testProcessor.endstopHigh or not passed:
            print "Reading endstops failed."
            state = "board fail"      
        else:     
            state = "endstop low"

    elif state == "endstop low":
        passed = True
        print "Testing endstops low..."
        for pin in endstopOutPins:
            passed &= controller.pinLow(pin)
        for pin in endstopInPins:
            testProcessor.endstopLow += target.readPin(pin)
        if -1 in testProcessor.endstopLow or not passed:
            print "Reading endstops failed."
            state = "board fail"
        else:
            state = "vrefs"

    elif state == "thermistors":
        print "Testing thermistor values..."
        for pin in thermistorPins:
            testProcessor.thermistors += target.analogRead(pin)
        if -1 in testProcessor.thermistors:
            print "Reading thermistors failed."
            state = "board fail"
        else:
            #state = "program marlin"
            targetMotorsDisable()
            time.sleep(1.5)
            if isOverCurrent(): state = "board fail"
            else: state = "program marlin"

    elif state == "program marlin":
        print "Disconnecting target from test server..."
        target.close()
        print "Programming target with vendor firmware..."
        if avrdude.upload(vendorFirmware, timeout = 20):
            state = "testamps"
            #state = "processing"
        else:
            print "Upload failed!"
            state = "board fail"

    elif state == "testamps":
        if isOverCurrent(): state = "board fail"
        state = "processing"

    elif state == "processing":
        if testProcessor.verifyAllTests():
            call(["./tpgrep.sh",serialNumber])
            print colored(serialNumber + " Board passed!", 'green')
            testProcessor.errors = "Passed" + testProcessor.errors
            with open(logFile, "a") as tpLog:
                tpLog.write(serialNumber + ' Passed\n')
            state = "finished"
        else:
            powerOff()
            call(["./tpgrep.sh",serialNumber])
            print colored(serialNumber + " Board failed!", 'red')
            testProcessor.errors = "Failed:" + testProcessor.errors
            with open(logFile, "a") as tpLog:
                tpLog.write(serialNumber + ' Failed\n')
            state = "enter code"
        testProcessor.showErrors()
        
    elif state == "board fail":
        powerOff()
        print "Unable to complete testing process!"
        print colored(serialNumber + " Board failed",'red')
        with open(logFile, "a") as tpLog:
            tpLog.write(serialNumber + ' Failed\n')
        testProcessor.verifyAllTests()
        testProcessor.showErrors()
        powerOff()
        testProcessor.errors = "Failed:" + testProcessor.errors
        print "Restarting test controller..."
        controller.restart()
        if target.serial.isOpen():
            print "Closing target..."
            target.close()
        #state = "finished"
	state = "enter code"

    elif state == "enter code":
	print "0 See Comments, 1 Valid Fail, 2 Board insertet incorrectly, 3 No Fuse, 4 Bootloader missing"
        print "Enter code for fail: "
        failCode = raw_input()
	if failCode == "0":
            print "Enter note for fail: "
            failNote = raw_input()
	state = "finished"
        
    elif state == "finished":
        print "Writing results to database..."
        testStorage = psycopg2.connect(postgresInfo)
        cursor = testStorage.cursor()
        #cursor.execute("""INSERT INTO testdata(serial, timestamp, testresults, testversion, testdetails, failure_code, failure_notes) VALUES (%s, %s, %s, %s, %s, %s, %s)""", (serialNumber, 'now', testProcessor.errors, version, str(testProcessor.resultsDictionary()), failCode, failNote ))
        cursor.execute("""INSERT INTO testdata(serial, timestamp, testresults, testversion, testdetails, failure_code, failure_notes, wave_operator, qc, tester, amps, gitdiff, gitbranch) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (serialNumber, 'now', testProcessor.errors, version, str(testProcessor.resultsDictionary()), failCode, failNote, waveOperator, qcPerson, testPerson, str(currentReadings), gitdiff, gitbranch ))
        testStorage.commit()
        testProcessor.restart()
        print "Preparing Test Jig for next board..."
        powerOff()
        if testjig == "rambo":
            controller.home(homingRate, wait = True)
        state = "start" 

