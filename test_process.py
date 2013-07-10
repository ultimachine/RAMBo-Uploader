#!/usr/bin/env python 

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

print "RAMBo Test Server"

#Configuration        
monitorPin = 44 #PL5 on test controller
triggerPin = 3 #bed on target board
powerPin = 3 #bed on test controller
homingRate = 5000
clampingRate = 4000
clampingLength = 18550
>>>>>>> modularity
monitorFrequency = 1000
stepperTestRPS = 3 #rotations per second for the stepper test
controllerPort = "/dev/ttyACM0"
targetPort = "/dev/ttyACM1"
testFirmwarePath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
testing = True
state = "start"
vrefPins = [8, 6, 5, 4, 3] #x, y, z, e0, e1 on controller
supplyPins = [7, 2] #extruder rail, bed rail on controller
mosfetOutPins = [9, 8, 7, 6, 3, 2] #On target
mosfetInPins = [44, 32, 45, 31, 46, 30] #On controller
thermistorPins = [0, 1, 2]


#def analogToVoltage(reading, voltage = 5, bits = 10):
#   array = []
#   for reading /pow(2,10))*voltage

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
testProcessor = TestProcessor()


#Setup shutdown handlers
def signal_handler(signal, frame):
    print "Shutting down test server..."
    controller.pinLow(powerPin)
    controller.home(homingRate, wait = False)
    controller.close()
    target.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

print "Test server started. Press CTRL-C to exit."
print "Monitoring test controller..."

while(testing):
    if state == "start":
        controller.waitForStart() #Blocks until button pressed
        state = "clamping"
        print "Test started at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            
    elif state == "clamping":
        print "Clamping test jig..."
        controller.home(rate = homingRate, wait = False)
        controller.runSteppers(frequency = clampingRate, steps = clampingLength,
                               direction = controller.UP, wait = False)
        state = "program for test"

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
            state = "wait for homing"
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
        if controller.pinHigh(powerPin):
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
        if -1 in testProcessor.fullStep:
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
        if -1 in testProcessor.halfStep:
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
        if -1 in testProcessor.quarterStep:
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
        if -1 in testProcessor.sixteenthStep:
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

    elif state == "supply test":
        print "Testing supply voltages..."
        for pin in supplyPins:
            testProcessor.supplys += controller.analogRead(pin)
        if -1 in testProcessor.supplys:
            print "Reading supplies failed."
            state = "board fail"
        else:     
            state = "mosfet high"
 
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
            state = "vrefs"

    elif state == "thermistors":
        print "Testing thermistor values..."
        for pin in thermistorPins:
            testProcessor.thermistors += target.analogRead(pin)
        if -1 in testProcessor.thermistors:
            print "Reading thermistors failed."
            state = "board fail"
        else:
            state = "program marlin"

    elif state == "program marlin":
        print "Disconnecting target from test server..."
        target.close()
        print "Programming target with vendor firmware..."
        if avrdude.upload(vendorFirmware, timeout = 20):
            state = "processing"
        else:
            print "Upload failed!"
            state = "board fail"

    elif state == "processing":
        testProcessor.verifyAllTests()
        state = "finished"
        testProcessor.showErrors()
        testProcessor.restart()
        
    elif state == "board fail":
        print "Unable to complete testing process!"
        print colored("Board failed",'red')
        controller.pinLow(powerPin)
        print "Restarting test controller..."
        controller.restart()
        print "Closing target..."
        if target.serial.isOpen():
            target.close()
        state = "finished"
        
    elif state == "finished":
        print "Preparing Test Jig for next board..."
        controller.pinLow(powerPin)
        controller.home(homingRate, wait = True)
        state = "start" 

