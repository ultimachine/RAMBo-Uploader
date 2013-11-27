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
import psycopg2
import serial.tools.list_ports
import configuration

print "RAMBo Test Server"
directory = os.path.split(os.path.realpath(__file__))[0]
try:
    version = subprocess.check_output(['git', '--git-dir='+directory+'/.git',
                                   'rev-parse', 'HEAD'])
except:
    print "Could not get git version"
    version = "unknown"
version = version.strip()
print "Git version - " + str(version)

print "Connecting to database..."
try:
    testStorage = configuration.database.open()
except:
    print "Could not connect!"
    sys.exit(0)

#Configuration
monitorPin = 44 #PL5 on test controller
triggerPin = 3 #bed on target board
powerPin = 3 #bed on test controller
monitorFrequency = 1000
stepperTestRPS = 3 #rotations per second for the stepper test
testing = True
state = "start"
serialNumber = ""
vrefPins = [8, 6, 5, 4, 3] #x, y, z, e0, e1 on controller [Analog-EXT-8, Analog-EXT-6, Analog-EXT-5, Analog-EXT-4, Analog-EXT-3]
supplyPins = [7, 2, 0] #extruder rail, bed rail, 5v rail on controller
mosfetOutPins = [3, 2, 6, 7, 8, 9] #On target  [Bed, Fan2, Fan1, Heat1, Fan0, Heat0] 
mosfetInPins = [44, 32, 45, 31, 46, 30] #On controller [MX1-5, MX1-4, MX2-5, MX2-4, MX3-5, MX3-4]
endstopOutPins = [83, 82, 81, 80, 79, 78] # on controller [EXT2-10, EXT2-12, EXT2-14, EXT2-16, EXT2-18, EXT2-20 ]
endstopInPins = [12, 11, 10, 24, 23, 30] # on target [xmin, ymin, zmin, xmax, ymax, zmax]
thermistorPins = [0, 1, 2, 7]; # on target [T0, T1, T2, T3]

def find_rambo_port(serial_number = None):
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "RAMBo" in port[1]:
            print "Found RAMBo board", port
            if serial_number is None:
                return port[0]
            elif serial_number in port[2]:
                print "Found port with correct serial : ", port
                return port[0]
        else:
            print "Ignoring non-RAMBo board", port

def find_target_port():
    ports = list(serial.tools.list_ports.comports())
    rambos = []
    for port in ports:
        if "RAMBo" in port[1]:
            ignore = False
            if port[0] == configuration.controller_port or port[2].endswith("SNR=%s" % configuration.controller_snr):
                ignore = True
            for snr in configuration.ignore_rambo_snr:
                if port[2].endswith("SNR=%s" % snr):
                    print "Ignoring this board ", port
                    ignore = True

            if ignore is False:
                rambos.append(port[0])
                
    print "Found these boards : ", rambos
    if len(rambos) != 1:
        return None
    return rambos[0]
    
def find_serial_number(from_port):
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if port[0] == from_port:
            snr = port[2].find("SNR=")
            if snr >= 0:
                return port[2][snr+4:]
            break
    return None
                
controllerPort = configuration.controller_port
targetPort = configuration.target_port
print list(serial.tools.list_ports.comports())

if controllerPort is None:
    controllerPort = find_rambo_port(configuration.controller_snr)
if controllerPort is None:
    print "Can't find controller board."
    sys.exit(0)

#Setup test interfaces
controller = TestInterface()
target = TestInterface()
if not controller.open(port = controllerPort):
    print "Check controller connection."
    sys.exit(0)
    
#Setup target test firmware object to pass to AVRDUDE.
testFirmware = Atmega()
testFirmware.name = "atmega2560"
testFirmware.bootloader = configuration.test_firmware_path

#Setup target vendor firmware object to pass to AVRDUDE. 
vendorFirmware = Atmega()
vendorFirmware.name = "atmega2560"
vendorFirmware.bootloader = configuration.vendor_firmware_path

#Setup up avrdude config for upload to an Arduino.
avrdude = Avrdude()
avrdude.path = configuration.avrdude_path
avrdude.programmer = configuration.serial_programmer
avrdude.port = targetPort
avrdude.baudrate = "115200"
avrdude.autoEraseFlash = True

#Define our test processor
testProcessor = TestProcessor()


#Setup shutdown handlers
def signal_handler(signal, frame):
    print "Shutting down test server..."
    controller.pinLow(powerPin)
    controller.close()
    target.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

print "Test server started. Press CTRL-C to exit."
print "Monitoring test controller..."

while(testing):
    if state == "start":
        controller.pinLow(powerPin)
        print "Press Enter to start test "
        raw_input()
        if configuration.icsp_program:
            state = "uploading"
        else:
            state = "program for test"
        print "Test started at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


    elif state == "uploading":
        print "Uploading Bootloader and setting fuses..."
        m32u2_image = Atmega()
        m32u2_image.name = "m32u2"
        m32u2_image.bootloader = configuration.m32u2_bootloader_path
        m32u2_image.lockBits = "0x0F"
        m32u2_image.extFuse = "0xF4"
        m32u2_image.highFuse = "0xD9"
        m32u2_image.lowFuse = "0xEF"

        m2560_image = Atmega()
        m2560_image.name = "m2560"
        m2560_image.bootloader = configuration.m2560_bootloader_path
        m2560_image.lockBits = "0x0F"
        m2560_image.extFuse = "0xFD"
        m2560_image.highFuse = "0xD0"
        m2560_image.lowFuse = "0xFF"

        icsp = Avrdude()
        icsp.path = configuration.avrdude_path
        icsp.verbose = 2
        icsp.verify = configuration.icsp_verify

        icsp.programmer = configuration.m32u2_icsp_programmer
        icsp.port = configuration.m32u2_icsp_port
        if icsp.upload(m32u2_image, timeout=60):
            icsp.programmer = configuration.m2560_icsp_programmer
            icsp.port = configuration.m2560_icsp_port
            if icsp.upload(m2560_image, timeout=120):
                state = "program for test"
                time.sleep(5)
            else:
                print "Upload failed."
                state = "board fail"
        else:
            print "Upload failed."
            state = "board fail"

    elif state == "program for test":
        print "Programming target with test firmware..."
        state = "connecting target"
        targetPort = configuration.target_port
        if targetPort is None:
            targetPort = find_target_port()
        if targetPort is None:
            print "Can't find target board."
            state = "board fail"
        else:
            avrdude.port = targetPort
            if avrdude.upload(testFirmware, timeout = 10):
                state = "connecting target"
            else:
                print "Upload failed."
                state = "board fail"

    elif state == "connecting target":
        print "Attempting connect..."   
        if target.open(port = targetPort):
            state = "powering"
        else:
            print "Connect failed."
            state = "board fail"

    elif state == "powering":   
        print "Powering Board..."
        if controller.pinHigh(powerPin):
            state = "supply test"
            time.sleep(configuration.powering_delay);
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
            state = "program marlin"

    elif state == "program marlin":
        print "Disconnecting target from test server..."
        target.close()
        print "Programming target with vendor firmware..."
        if avrdude.upload(vendorFirmware, timeout = 20):
            state = "processing"
            time.sleep(1)
        else:
            print "Upload failed!"
            state = "board fail"

    elif state == "processing":
        if testProcessor.verifyAllTests():
            print colored("Board passed!", 'green')
            testProcessor.errors = "Passed" + testProcessor.errors
        else:
            print colored("Board failed!", 'red')
            testProcessor.errors = "Failed:" + testProcessor.errors
        state = "finished"
        testProcessor.showErrors()

        
    elif state == "board fail":
        print "Unable to complete testing process!"
        print colored("Board failed",'red')
        testProcessor.verifyAllTests()
        testProcessor.showErrors()
        controller.pinLow(powerPin)
        testProcessor.errors = "Failed:" + testProcessor.errors
        print "Restarting test controller..."
        controller.restart()
        if target.serial.isOpen():
            print "Closing target..."
            target.close()
        state = "finished"
        
    elif state == "finished":
        print "Writing results to database..."
        configuration.database.post(find_serial_number(targetPort), testProcessor.errors, version, str(testProcessor.resultsDictionary()))
        testProcessor.restart()
        print "Preparing Test Jig for next board..."
        controller.pinLow(powerPin)
        state = "start" 

