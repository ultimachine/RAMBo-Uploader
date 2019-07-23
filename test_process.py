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
import termios
import datetime
import finishedGoods
from Board import *
from compatible_mode_programmable_psu_interface import *  #COMP (COMPatibility commands) see 663xxprg.pdf
from programmable_psu_interface import * #SCPI (Standard Commands for Programmable Instruments) see 663xxprg.pdf
from direct_psu_interface import *

print "RAMBo Test Server"
directory = os.path.split(os.path.realpath(__file__))[0]
version = subprocess.check_output(['git', '--git-dir='+directory+'/.git', 'rev-parse', 'HEAD'])
version = version.strip()
print "Git version - " + str(version)

gitdiff = subprocess.Popen( shlex.split('/usr/bin/git --git-dir='+directory+'/.git diff --exit-code --quiet') ).wait()
#if not running "test_process.py" then set gitdiff to indicate we're not running a clean test program.
if os.path.split(os.path.realpath(__file__))[1] != "test_process.py":
    gitdiff = 1

gitstatus = subprocess.check_output(shlex.split('git status --porcelain'))
for line in gitstatus.splitlines():
  if line.split()[0] == 'M': gitdiff = 1

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
powerPin = 3 #bed on test controller
homingRate = 8000 #5000
clampingRate = 7000 #4000
clampingLength = 15980 #16200
monitorFrequency = 1000
stepperTestRPS = 4 #3 #rotations per second for the stepper test
controllerPort = None
testing = True
state = "start"
serialNumber = ""
supplyPins = [7, 2, 0] #extruder rail, bed rail, 5v rail on controller
logFile = os.getenv("HOME") + '/tplog.txt'
relayBedMotorsPin = 4
relayBedPin = 4
relayLogicPin = 5
relayMotorsPin = 2
overCurrentChecking = True
currentReadings = []
saveFirmware = False
btldrState = True
bootloadOnlyMode = False

testStorage = psycopg2.connect(postgresInfo)
cursor = testStorage.cursor()

waveOperator = None
qcPerson = None
testPerson = None

targetPort = "/dev/ttyACM" + sys.argv[1]
print "targetPort: " + targetPort
if sys.argv[2] == "rambo":
  board = Rambo()
if sys.argv[2] == "minirambo":
  board = MiniRambo()
if sys.argv[2] == "einsyrambo":
  board = EinsyRambo()
if sys.argv[2] == "archim":
  board = ArchimRambo()
if sys.argv[2] == "PrusaEinsy":
  board = PrusaEinsy()
if sys.argv[2] == "UltimachineEinsy":
  board = UltimachineEinsy()
if sys.argv[2] == "EinsyRetro":
  board = EinsyRetro()
if sys.argv[2] == "UltiEinsyPrusaFirmware":
  board = UltiEinsyPrusaFirmware()
if sys.argv[2] == "EinsyPrusaMK3Firmware":
  board = EinsyPrusaMK3Firmware()

controllerPorts  = ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_74035323434351A00261-if00"] #10006390 Rambo Controller
controllerPorts += ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_74034313938351C0A291-if00"] #10024352 Rambo Controller
controllerPorts += ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_55539333937351615271-if00"] #10059679 Mini-Rambo Controller
controllerPorts += ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_5553933393735151A2A1-if00"] #10059735 Backup Controller
controllerPorts += ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_55533343837351102242-if00"] #10059099 Bench/Archim Controller
controllerPorts += ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_75530313331351713281-if00"] #Einsy Controller
controllerPorts += ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_5553933393735141E1E1-if00"] #Einsy Controller
controllerPorts += ["/dev/serial/by-id/usb-UltiMachine__ultimachine.com__RAMBo_75530313231351E070B1-if00"] #Einsy Controller

for item in controllerPorts:
    if os.path.exists(item): controllerPort = item

# USB Firmware
if len(sys.argv) >= 4:
    usbfw = sys.argv[3]
else:
    usbfw = '/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX'


#Setup test interfaces
controller = board.controller #TestInterface()
target = board.target #TestInterface()
if not controller.open(port = controllerPort):
    print "Check controller connection."
    sys.exit(0)

print( colored('dbg controller serial write color', controller.writeColor, attrs=controller.writeAttrs) )

print( colored('dbg controller seral response color', controller.responseColor, attrs=controller.responseAttrs) )

target.writeAttrs = ['bold']
print( colored('dbg target serial write color', target.writeColor, attrs=target.writeAttrs) )

target.responseAttrs = ['bold']
print( colored('dbg target seral response color', target.responseColor, attrs=target.responseAttrs) )

psuPorts  = ["/dev/serial/by-id/usb-Prologix_Prologix_GPIB-USB_Controller_PX9LUIO9-if00-port0"]
#psuPorts += ["/dev/serial/by-id/usb-Prologix_Prologix_GPIB-USB_Controller_PX2CJNJB-if00-port0"]
psuPort = "/dev/ttyUSB0"

for item in psuPorts:
    if os.path.exists(item): psuPort = item

psu = CompatProgrammablePSU()
#psu = ProgrammablePSU()
#psu = DirectPSU()
psu.controller = controller
psu.open(port = psuPort)

#Setup up avrdude config for upload to an Arduino.
avrdude = Avrdude()
avrdude.path = "/usr/bin/avrdude"
avrdude.programmer = "wiring" #stk500v2
avrdude.port = targetPort
avrdude.baudrate = "115200"
avrdude.autoEraseFlash = True

testProcessor = board.testProcessor

thresholdCurrent = board.thresholdCurrent

#Setup shutdown handlers
def signal_handler(signal, frame):
    print "Shutting down test server..."
    powerOff()
    #controller.home(homingRate, wait = False)
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
    print testProcessor.supplyNames
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
def powerOn_OLD():
                 controller.pinHigh(powerPin)
                 controller.pinHigh(relayBedMotorsPin)
                 return controller.pinHigh(relayLogicPin)

def powerOn():
                 psu.on()

def powerOff():
                 psu.off()

def powerOff_OLD():
                 controller.pinLow(powerPin)
                 #controller.pinLow(relayBedMotorsPin)
                 #controller.pinLow(relayLogicPin)
def smpsOn():
                 controller.pinLow(9)
                 time.sleep(0.1)


def smpsOff():
                 controller.pinHigh(9)

def readCurrent():
                 adcReadings = []

                 time.sleep(0.1)
                 for count in range(5):
                      controller.analogRead(1)
                 for count in range(20):
                      adcReadings += controller.analogRead(1)
                 return round(sum(adcReadings)/len(adcReadings) * (5.0/1024.0),4)

def read_psu_current():
                psu.sendquery(b"IOUT?")
                time.sleep(0.5)
                value_amps = psu.readValue().strip()
                try:
                    value_amps = float(value_amps)
                except:
                    sys.stdout.write("ERROR reading value from PSU...\n")
                    return -1
                return value_amps

def isOverCurrent(threshold):
                 if not overCurrentChecking: 
                     return False

                 amps = read_psu_current() #readCurrent()

                 currentReadings.append(amps)

                 if(amps > threshold):
                     powerOff()
                     testProcessor.errors += "Over " + str(threshold) + " amps\n"
                     print colored("Board is OVER MAXIMUM current threshold: " + str(threshold),'red')
                     print colored("Check for reverse capacitor or short circuit...",'yellow')
                     return True
                 return False

def isOverCurrentBedMotors():
                  controller.pinHigh(relayBedMotorsPin)
                  return isOverCurrent(0.0)


def isOverCurrentLogic():
                  controller.pinLow(relayBedMotorsPin)
                  controller.pinHigh(relayLogicPin)
                  return isOverCurrent(board.thresholdCurrent)

def targetMotorsDisable():
                 board.disableMotors()
                 #ramboMotorEnablePins = [29,28,27,26,25]
                 #for enablePin in ramboMotorEnablePins:
                 #     target.pinHigh(enablePin)

def beep():
                    call(["beep","-f 2250"])

def programBootloaders():
        #icsp_uid_32u2 = "000200172397"
        icsp_uid_32u2 = "000203212345"
        #icsp_uid_32u2 = "000200312345"
        time.sleep(1) #2560 AVR ICSP is powered by the board and needs more time to be recognized by the linux computer.
        #usbfw = '/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX'
        #usbfw = '/home/ultimachine/Prusa-usbserial.hex'
        #bootcmd32u2 = '/usr/bin/timeout 10 /usr/bin/avrdude -s -v -v -V -b 1000000 -p atmega32u2 -P usb:000203212345 -c avrispmkII -e -Uflash:w:' + usbfw + ':i -Uefuse:w:0xF4:m -Uhfuse:w:0xD9:m -Ulfuse:w:0xEF:m -Ulock:w:0x0F:m'
        bootcmd32u2 = '/usr/bin/timeout 10 /usr/bin/avrdude -s -v -v -V -p atmega32u2 -P usb:' + icsp_uid_32u2 +  ' -c avrispmkII -e -Uefuse:w:0xF4:m -Uhfuse:w:0xD9:m -Ulfuse:w:0xEF:m -Ulock:w:0xCF:m -Uflash:w:' + board.firmware32u2 + ':i'

        #bootcmd2560 = '/usr/bin/timeout 10 /usr/bin/avrdude -s -v -v -V -b 1000000 -p m2560      -P usb:000200212345 -c avrispmkII -e -Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/stk500boot_v2_mega2560.hex:i -Uefuse:w:0xFD:m -Uhfuse:w:0xD0:m -Ulfuse:w:0xFF:m -Ulock:w:0x0F:m'
        #bootcmd2560 = '/usr/bin/timeout 10 /usr/bin/avrdude -s -v -v -V -b 1000000 -p m2560      -P usb:000200212345 -c avrispmkII -e -Uflash:w:/home/ultimachine/workspace/Einsy/stk500v2-prusa/stk500v2-prusa.hex:i -Uefuse:w:0xFD:m -Uhfuse:w:0xD0:m -Ulfuse:w:0xFF:m -Ulock:w:0x0F:m'
        bootcmd2560 = '/usr/bin/timeout 10 /usr/bin/avrdude -s -v -v -V -p m2560      -P usb:000200212345 -c avrispmkII -e -Uefuse:w:0xFD:m -Uhfuse:w:0xD0:m -Ulfuse:w:0xFF:m -Ulock:w:0xCF:m -Uflash:w:' + board.bootloader2560 + ':i'
        bootloader32u2 = subprocess.Popen( shlex.split( bootcmd32u2 ), stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
        bootloader32u2.wait()
        bootloader2560 = subprocess.Popen( shlex.split( bootcmd2560 ), stderr = subprocess.STDOUT, stdout = subprocess.PIPE)
        bootloader2560.wait()

        logmsg=serialNumber + " "
        if bootloader2560.returncode:
                print bootloader2560.communicate()[0]
                msg = colored("2560 Btldr FAILED!! ",'red')
                logmsg = logmsg + msg + str(bootloader2560.returncode)
                print msg
        if bootloader2560.returncode == 0:
                msg = colored("2560 Btldr Success! ",'green')
                logmsg = logmsg + msg
                print msg
        if bootloader32u2.returncode:
                print bootloader32u2.communicate()[0]
                msg = colored("32u2 Btldr FAILED!! ",'red')
                logmsg = logmsg + msg + str(bootloader32u2.returncode)
                print msg
        if bootloader32u2.returncode == 0:
                msg = colored("32u2 Btldr Success! ",'green')
                logmsg = logmsg + msg
                print msg

        if bootloader32u2.returncode or bootloader2560.returncode:
                return 1
                #state = "board fail"
                #continue

        fusescmd32u2 = '/usr/bin/timeout 6 /usr/bin/avrdude -b 1000000 -p atmega32u2 -P usb:' + icsp_uid_32u2 +  ' -c avrispmkII -Uefuse:v:0xF4:m -Uhfuse:v:0xD9:m -Ulfuse:v:0xEF:m -Ulock:v:0xCF:m'
        fusescmd2560 = '/usr/bin/timeout 6 /usr/bin/avrdude -b 1000000 -p m2560      -P usb:000200212345 -c avrispmkII -Uefuse:v:0xFD:m -Uhfuse:v:0xD0:m -Ulfuse:v:0xFF:m -Ulock:v:0xCF:m'
        verifyfuses32u2 = subprocess.Popen( shlex.split( fusescmd32u2 ), stderr = subprocess.STDOUT, stdout = subprocess.PIPE )
        verifyfuses32u2.wait()
        verifyfuses2560 = subprocess.Popen( shlex.split( fusescmd2560 ), stderr = subprocess.STDOUT, stdout = subprocess.PIPE )
        verifyfuses2560.wait()

        if verifyfuses2560.returncode:
                print verifyfuses2560.communicate()[0]
                msg = colored("2560 Fuses FAILED!! ",'red')
                logmsg = logmsg + msg + str(verifyfuses2560.returncode)
                print msg
        if verifyfuses2560.returncode == 0:
                msg = colored("2560 Fuses Success! ",'green')
                logmsg = logmsg + msg
                print msg
        if verifyfuses32u2.returncode:
                print verifyfuses32u2.communicate()[0]
                msg = colored("32u2 Fuses FAILED!!",'red')
                logmsg = logmsg + msg + str(verifyfuses32u2.returncode) + "\n"
                print msg
        if verifyfuses32u2.returncode == 0:
                msg = colored("32u2 Fuses Success!",'green')
                logmsg = logmsg + msg + "\n"
                print msg
        with open(directory + "/boot.log", "a") as bootlog:
                bootlog.write(logmsg)
                bootlog.close()

        if verifyfuses32u2.returncode or verifyfuses2560.returncode:
                return 1
                #state = "board fail"

        #if bootloader is successful
        return 0

def printHelp():
		print "List of commands: \n"
		print "help: show this list \n"
		print "p: power on (set powerPin and relay BedMotorsPin high) \n" 
		print "o: power off (set powerPin and relayBedMotorsPin low)\n"
		print "r: set rambo config \n"
		print "m: set minirambo config \n"
		print "h: return test jig to start position \n"
		print "b: toggle bootloader \n"
		print "c: clamp test jig \n"
		print "s: supply test \n"
		print "a: current test \n"
		print "id: print internal serial id \n"
                print "btonly: toggle bootloader only mode"

def set_run_id():
    cursor.execute("""SELECT serial, timestamp,productionrunid,testjig FROM public.testdata WHERE testjig=%s ORDER BY timestamp DESC LIMIT 1""", (board.testjig,))
    rows = cursor.fetchall()
    if len(rows) == 0 or rows[0][2] == None:
	orderRunId = board.id
    else:
	orderRunId = rows[0][2]
	cursor.execute("""SELECT * FROM productionruns WHERE productionRunId=%s""",(orderRunId,))
	rows2 = cursor.fetchall()
	if len(rows2) == 0:
	    orderRunId = board.id
	else:
	    orderRunId = rows[0][2]
    return orderRunId

def print_run_id_info(runID,testjig):
    cursor.execute("""SELECT productionrunid, productid, productionrunname, shipdate, shipqty,endqty FROM public.productionruns WHERE productionrunid=%s""",(runID,))
    rows = cursor.fetchall()
    print "Current run id: ",rows[0][0]," for ", board.testjig,".  Current order for: ",rows[0][2],". Shipping date: ",rows[0][3],". Order quantity: ",rows[0][4],". Current count: ",rows[0][5]

def get_count_for_runid(runID):
    cursor.execute("""SELECT serial,testresults,productionrunid FROM public.testdata WHERE testresults='Passed' AND productionrunid=%s GROUP BY serial,testresults,productionrunid """, (runID,))
    rowsCount = cursor.fetchall()
    count = len(rowsCount)
    return count

def test_diags(drive_mode_name,drive_mode=2):
        print "Testing diags " + str(drive_mode_name) + "..."
        diag_results = []
        target.set_trinamic_diag_mode(drive_mode)
        for pin in board.diagPins:
            diag_results += target.pullupReadPin(pin)
        if -1 in diag_results:
            print "Reading diags failed."
        print str(diag_results)
        return diag_results

def test_diags_highREFACTOR2():
        testProcessor.diagsHigh = test_diags("high",2); #2 = open drain
        if -1 in testProcessor.diagsHigh:
            return -1
        return 0

def test_diags0_lowREFACTOR2():
        testProcessor.diags0_Low = test_diags("0 low",0); #2 = open drain
        if -1 in testProcessor.diags0_Low:
            return -1
        return 0

def test_diags_high():
        print "Testing diags high..."
        target.set_trinamic_diag_mode(2)
        for pin in board.diagPins:
            testProcessor.diagsHigh += target.pullupReadPin(pin)
            #testProcessor.diagsHigh = [0,0,0,0] #FAIL TEST
        if -1 in testProcessor.diagsHigh:
            print "Reading diags failed."
            return -1
        else:
            print str(testProcessor.diagsHigh)
            return 0

def test_diags0_low():
        print "Testing diags0 low..."
        target.set_trinamic_diag_mode(0)
        for pin in board.diagPins:
            testProcessor.diags0_Low += target.pullupReadPin(pin)
            #testProcessor.diags0_Low = [1,1,1,1] #FAIL TEST
        if -1 in testProcessor.diags0_Low:
            print "Reading diags failed."
            return -1
        else:
            print str(testProcessor.diags0_Low)
            return 0

def test_diags1_low():
        print "Testing diags1 low..."
        target.set_trinamic_diag_mode(1)
        for pin in board.diagPins:
            testProcessor.diags1_Low += target.pullupReadPin(pin)
            #testProcessor.diags1_Low = [1,1,1,1] #FAIL TEST
        target.set_trinamic_diag_mode(2) #Enables GCONF EXT VREF again
        if -1 in testProcessor.diags1_Low:
            print "Reading diags failed."
            return -1
        else:
            print str(testProcessor.diags1_Low)
            return 0

orderRunId = set_run_id()

while(testing):
    #controller.setMotorCurrent(255)
    if state == "start":
        print 'usbfw: ' + colored(usbfw,'yellow')
	failCode = None
	failNote = None
        currentReadings = []
        iserial = None

        while True:
            iserial = None
            if gitdiff == 1:
                 print colored("Warning: Not a CLEAN program. Alert your nearest administrator immediately!",'red')
	    finishedGoods.main(datetime.date.today(),cursor,testStorage,testjig=board.testjig)
	    print_run_id_info(orderRunId, board.testjig)
            print colored("Enter serial number : ","cyan")
            serialNumber = sys.stdin.readline().strip() #raw_input().strip()
	    if serialNumber == "sr": #select runid
		print "productionrunid | productionrunname | shipdate| shipqty"
		cursor.execute("""SELECT productionrunid,productionrunname,shipdate,shipqty FROM public.productionruns ORDER BY productionrunid""")
		rows = cursor.fetchall()
		count = len(rows)
                for line in rows:
                    print line
		print "Please select a new productionRunId or c to cancel"
		newOrderRunId = sys.stdin.readline().strip()
		try:
		    newOrderRunId = int(newOrderRunId)
		except:
		    print "That is not a number"
		    continue
		if newOrderRunId == "c":
		    continue
		else:
			cursor.execute("""SELECT productionrunid FROM public.productionruns WHERE productionrunid=%s""",(newOrderRunId,))
			rows = cursor.fetchall()
			count = len(rows)
			if count==0:
		    	    print "That run id does not exist."
			else:
		    	    orderRunId = newOrderRunId
		    	    print "The run id is now set to: ",orderRunId
		            continue
	    if serialNumber == "co": #count runid
                cursor.execute("""SELECT serial,testresults,productionrunid FROM public.testdata WHERE testresults='Passed' AND productionrunid=%s GROUP BY serial,testresults,productionrunid""", (orderRunId,))
                rows = cursor.fetchall()
		count = len(rows)
		print(count)
		continue
	    if serialNumber=="help":
		printHelp()
		continue
	    if serialNumber=="flash":
		print "SPIFLASH ID: " + str(target.initSpiflash())
		print "SDCARD: " + str(target.initSdcard())
		continue
	    if serialNumber=="nrst":
		board.toggle_nrst()
		continue
	    if serialNumber=="samba":
		board.samba_mode()
		continue
	    if serialNumber=="exit":
		print "Exiting"
		sys.exit()
            if serialNumber == "m":
                 board = MiniRambo()
                 continue
            if serialNumber == "r":
                 board = Rambo()
                 continue
            if serialNumber == "cr":
                 print "Restarting controller"
                 controller.restart()
                 continue

	    if serialNumber== "ldr" or serialNumber== "b":
		 if btldrState == True:
			btldrState = False
			print "Bootloader is now off"
		 else:
			print "Bootloader is now on"
			btldrState = True
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
                 print board.testProcessor.supplyNames
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
            if serialNumber == "smpsoff":
                 controller.pinHigh(9)
                 continue
            if serialNumber == "smpson":
                 controller.pinLow(9)
                 continue
            if serialNumber == "id":
                 print str(getInternalSerialNumber())
                 continue
            if serialNumber == "moton":
                 controller.pinHigh(relayMotorsPin)
                 continue
            if serialNumber == "motoff":
                 controller.pinLow(relayMotorsPin)
                 continue
            if serialNumber == "j":
                 powerOn()
                 isOverCurrent(board.thresholdCurrent)
                 time.sleep(0.5)
                 isOverCurrent(board.thresholdCurrent)
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
            if serialNumber == "btmode":
                 import serial
                 s = serial.Serial(port="/dev/ttyACM1",baudrate=1200)
                 try:
                   s.open()
                   s.close()
                 except:
                   print "SAMBA mode."
                   s.close()
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
                 isOverCurrent(board.thresholdCurrent)
                 time.sleep(3)
                 isOverCurrent(board.thresholdCurrent)
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
                 avrdude.upload(board.testFirmware, timeout = 10)
                 continue
            if serialNumber == "savefw":
                 print "Enabling Save FW"
                 saveFirmware = True
                 continue
            if serialNumber == "eh":
                ehresults = []
                if board.testjig == "einsyretro":
                    target.pinLow(53) #Drive SDCard Chip Select low to test the MISO buffer. The miso buffers enable pin is connected to SDSS
                if board.testjig == "einsyrambo":
                    target.pinLow(77) #Drive SDCard Chip Select low to test the MISO buffer. The miso buffers enable pin is connected to SDSS
		print "Testing endstops high..."
		for pin in board.endstopOutPins:
		    passed = controller.pinHigh(pin)
		for pin in board.endstopInPins:
		    ehresults += target.pullupReadPin(pin)
		if -1 in testProcessor.endstopHigh:
		    print "Reading endstops failed."
                print "names: " + str(testProcessor.endstopNames)
                print "endstops high results: " + str(ehresults)
                continue
            if serialNumber == "el":
                print "Testing endstops low..."
                ehresults=[]
                for pin in board.endstopOutPins:
                    controller.pinLow(pin)
                for pin in board.endstopInPins:
                    ehresults += target.readPin(pin)
                if -1 in testProcessor.endstopLow:
                    print "Reading endstops failed."
                print "names: " + str(testProcessor.endstopNames)
                print "endstops low results: " + str(ehresults)
                continue
            if serialNumber == "i2c":
                ehresults = []
		print "Testing i2c pins low..."
		for pin in board.I2CPins:
                    passed = target.pinLow(pin)
                    time.sleep(0.01)
                    ehresults += target.readPin(pin)
                    target.pullupReadPin(pin)
                print "names: " + str(["SDA", "SCL"])
                print "results: " + str(ehresults)
		if -1 in ehresults or not passed:
		    print "Reading i2c pins failed."
                if ehresults != [0,0]:
                    print "I2C Pullup Test Failed (not [0,0]). Stopping Test."
                continue
            if serialNumber == "dh":
                dhresults = []
		print "Testing diag pins high..."
                target.set_trinamic_diag_mode(2)
		for pin in board.diagPins:
		    dhresults += target.pullupReadPin(pin)
		if -1 in dhresults:
		    print "Reading diags failed."
                print "names: " + str(["X diag", "Y diag", "Z diag", "E diag"])
                print "results: " + str(dhresults)
                continue
            if serialNumber == "dl":
                dl_results = []
		print "Testing diag0 pins low..."

		target.set_trinamic_diag_mode(0)
		for pin in board.diagPins:
		    dl_results += target.pullupReadPin(pin)
		if -1 in dl_results:
		    print "Reading diags failed."
                print "names: " + str(["X diag0", "Y diag0", "Z diag0", "E diag0"])
                print "diag0 low results: " + str(dl_results)
                continue
            if serialNumber == "d":
                diag_results = []
		print "Testing diag0 pins low..."
		for pin in board.diagPins:
		    diag_results += target.pullupReadPin(pin)
		if -1 in diag_results:
		    print "Reading diags failed."
                print "names: " + str(["X diag", "Y diag", "Z diag", "E diag"])
                print "diag results: " + str(diag_results)
                continue

            if serialNumber == "btonly":
                if bootloadOnlyMode == True:
                    print "Boot Only Mode Disabled"
                    bootloadOnlyMode = False
                else:
                    print "Boot Only Mode ENABLED"
                    bootloadOnlyMode = True
                continue
            if serialNumber == "psu":
                psu.open()
                continue
            if serialNumber == "pc":
                psu.close()
                continue
            if serialNumber == "pr":
                psu.serial.write(b"++read eoi\n")
                print psu.read()
                continue
            if serialNumber == "w":
                print "psu read:"
                print psu.read()
                continue
            if serialNumber == "pi":
                psu.sendquery(b"ID?") #*IDN?
                continue
            if serialNumber == "pv":
                psu.showSetVoltage()
                psu.showSetCurrent()
                continue
            if serialNumber == "pa":
                sys.stdout.write( "readValue: ")
                psu.sendquery(b"IOUT?")
                time.sleep(0.5)
                value_amps = psu.readValue().strip()
                try:
                    value_amps = float(value_amps)
                except:
                    sys.stdout.write("ERROR reading value from PSU\n")
                    continue
                sys.stdout.write( str(value_amps) + "\n" )
                continue
            if serialNumber == "q":
                psu.sendquery(b"STS?")
                sys.stdout.write("STS?: ")
                #time.sleep(0.2)
                #psu.serial.write(b"++read eoi\n")
                #time.sleep(0.2)
                #time.sleep(0.1)
                #print psu.read().strip()
                print colored(psu.read().strip(),'blue',attrs=['bold'])
                continue
            if serialNumber == "sts":
                sys.stdout.write( "psu status: ")
                psu.sendquery(b"STS?")
                time.sleep(0.5)
                value_status = psu.readValue() #.strip()
                try:
                    value_status = float(value_amps)
                except:
                    sys.stdout.write("ERROR reading value from PSU\n")
                    continue
                sys.stdout.write( str(value_status) + "\n" )
                continue
            if serialNumber == "st":
                psu.showStatus()
                continue
            if serialNumber == "pm":
                psu.showMeasuredCurrent()
                continue
            if serialNumber == "pon":
                psu.on()
                continue
            if serialNumber == "poff":
                psu.off()
                continue
            if serialNumber == "mh":
                print "Testing MOSFETs high..."
                passed = True
                readings = []
                for pin in board.mosfetOutPins:
                    passed &= target.pinHigh(pin)
                for pin in board.mosfetInPins:
                    readings += controller.pullupReadPin(pin)
                if -1 in testProcessor.mosfetHigh or not passed:
                    print "Reading mosfets failed."
                print "mosfets high: " + str(readings)
                continue
            if serialNumber == "ml":
                print "Testing MOSFETs low..."
                passed = True
                readings = []
                for pin in board.mosfetOutPins:
                    passed &= target.pinLow(pin)
                for pin in board.mosfetInPins:
                    readings += controller.pullupReadPin(pin)
                if -1 in testProcessor.mosfetLow or not passed:
                    print "Reading mosfets failed."
                print "mosfets low: " + str(readings)
                continue
            try: 
                sNum = int(serialNumber)
                if(  (sNum in range(10000000,11000000))  or  (sNum in range(55500000,55555555)) or  (sNum in range(20000000,20100000))): 
                    break
                else:
                    print "Invalid Entry. (Use 55500000-55555555 for Testing)."
                    call(["beep","-f 2250"])
            except: 
                print "Error!  That was not a valid entry. Try again... (Use 55500000-55555555 for Testing)"
                call(["beep","-f 2250"])

        print "Testjig is now: " + board.testjig
        print "VendorFirmware:" + board.vendorFirmwarePath

	#call(["cat", "~/tplog.txt | grep " + serialNumber])
	call([directory + "/tpgrep.sh",str(serialNumber)])
        with open(logFile, "a") as tpLog:
            tpLog.write(serialNumber + '\n') 

        print "Press button to begin test"
        controller.waitForStart() #Blocks until button pressed

        state = board.setState()

        iserial = board.setISerial(targetPort)
        if not btldrState and iserial == 0  and len(sys.argv) >= 4:
            state = "start"
            continue

        if iserial != 0:
	    #Consistent iserial check: verify iserial matches first historical iserial number for the referenced serial number
	    cursor.execute("""SELECT "tid","serial","iserial" FROM "public"."testdata" WHERE tid = (SELECT MIN(tid) FROM public.testdata WHERE "serial" = %s AND "iserial" IS NOT NULL)""", (serialNumber,) )
	    rows = cursor.fetchall()
	    if(len(rows)):
	      print "historial: ", rows
	      print "this 32u2 iserial: ", iserial
	      if not iserial == str(rows[0][2]):
	        print colored("Warning! This serial number was previously tested with a different 32u2 iserial. This board may have a duplicate serial number.",'yellow')
	        state = "start"
	        continue

	    #Prevent extra serial numbers attached to single board by checking a boards first assigned serial number. 
            #Example situation: retesting a board but scanning a fresh boards serial number. 
            #lookup previous tests by iserial
	    cursor.execute("""SELECT "tid","serial","iserial" FROM "public"."testdata" WHERE tid = (SELECT MIN(tid) FROM public.testdata WHERE "iserial" = %s)""", (iserial,) )
	    rows = cursor.fetchall()
	    if(len(rows)):
	      print "historial: ", rows
	      print "this 32u2 iserial: ", iserial
	      if not serialNumber == str(rows[0][1]):
	        print colored("Warning! This board was first tested with a different serial number then the one provided. Try again with the correct serial number.",'yellow')
	        state = "start"
	        continue

        if iserial == 0:
            iserial = None #prevent zero from getting stored in db as the iserial.

        print "Test started at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    elif state == "clamping":
        smpsOff()
        print "Clamping test jig..."
        controller.home(rate = homingRate, wait = False)
        controller.runSteppers(frequency = clampingRate, steps = clampingLength,
                               direction = controller.UP, wait = False)
        state = "wait for homing"
#        state = "program for test"

    elif state == "uploading":
        if board.testjig == "archim":
            state = "program for test"
            continue
        state = "iserialcheck"

        if btldrState==True:
            print "Uploading Bootloader and setting fuses..."
        #avr32u2 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158420', u'-patmega32u2', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX:i', u'-Uefuse:w:0xF4:m', u'-Uhfuse:w:0xD9:m', u'-Ulfuse:w:0xEF:m', u'-Ulock:w:0x0F:m'])
        #avr2560 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158597', u'-pm2560', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/stk500boot_v2_mega2560.hex:i', u'-Uefuse:w:0xFD:m', u'-Uhfuse:w:0xD0:m', u'-Ulfuse:w:0xFF:m', u'-Ulock:w:0x0F:m'])
            if sys.argv[2] == "einsyrambo":
                time.sleep(1);
            if programBootloaders():
                print colored("Trying to program bootloaders again..",'yellow')
                if programBootloaders():
                    state = "board fail"

    elif state == "iserialcheck":
        state = "program for test"
        time.sleep(1) #0.8

        #get iserial
        iserial = board.setISerial(targetPort)

        #custom usbfw has no iserial
        if iserial == 0 and len(sys.argv) >= 4:
                iserial = None
                continue

        #fail if no iserial
        if iserial == 0:
                iserial = None
                state = "board fail"
                continue

        #Duplicate serial check: verify iserial matches first historical iserial number for the referenced serial number
        cursor.execute("""SELECT "tid","serial","iserial" FROM "public"."testdata" WHERE tid = (SELECT MIN(tid) FROM public.testdata WHERE "serial" = %s AND "iserial" IS NOT NULL)""", (serialNumber,) )
        rows = cursor.fetchall()
        if(len(rows)):
                print "historial: ", rows
                print "this 32u2 iserial: ", iserial
                if not iserial == str(rows[0][2]):
                        print colored("Warning! This serial number was previously tested with a different 32u2 iserial. This board may have a duplicate serial number.",'yellow')
                        state = "board fail"
                        continue

        #time.sleep(2)
    elif state == "program for test":
        if board.testjig == "archim":
            state = board.programTestFirmware()
            continue

        if bootloadOnlyMode==True:
            state = "program marlin"
            continue
        #bootloader verification over USB
        #verify2560bootloader_cmd = '/usr/bin/timeout 40 /usr/bin/avrdude -s -p m2560 -P ' + targetPort + ' -c wiring -Uflash:v:' + directory + '/stk500boot_v2_mega2560.hex:i -Uefuse:v:0xFF:m -Uhfuse:v:0xD0:m -Ulfuse:v:0xFF:m'

        #verify2560bootloader_cmd = '/usr/bin/timeout 40 /usr/bin/avrdude -s -p m2560 -P ' + targetPort + ' -c wiring -Uflash:v:' + '/home/ultimachine/workspace/Einsy/stk500v2-prusa' + '/stk500v2-prusa.hex:i -Uefuse:v:0xFF:m -Uhfuse:v:0xD0:m -Ulfuse:v:0xFF:m'
        verify2560bootloader_cmd = '/usr/bin/timeout 40 /usr/bin/avrdude -s -p m2560 -P ' + targetPort + ' -c wiring -Uflash:v:' + board.bootloader2560 + ':i -Uefuse:v:0xFD:m -Uhfuse:v:0xD0:m -Ulfuse:v:0xFF:m'
        verify2560bootloader_process = subprocess.Popen( shlex.split( verify2560bootloader_cmd ) )
        if verify2560bootloader_process.wait():
                print colored("2560 Bootloader Verification FAILED!! ",'red')
                state = "board fail"
                continue
        else:
                print colored("2560 Bootloader Verification Success! ",'green')

        print "Programming target with test firmware..."
        if saveFirmware:
            print "Saving Firmware!!!"
            savefilename = "/home/ultimachine/fw/" + serialNumber + time.strftime(".%Y.%m.%d.%H.%M")
            savefwcmd = "avrdude -V -pm2560 -cwiring -Uflash:r:"+savefilename+".hex:i -Ueeprom:r:"+savefilename+".eeprom:i -P"+targetPort
            savefwproc = subprocess.Popen(shlex.split(savefwcmd)).wait()

        if avrdude.upload(board.testFirmware, timeout = 10):
            state = "connecting target"
        else:
            print "Upload failed."
            state = "board fail"

    elif state == "connecting target":
        print "Attempting connect..."   
        if target.open(port = targetPort):
            state = "i2c floating"
            #state = "mosfet high"
            #state = "spiflashid"
            #state = "mosfet high"
            #state = "wait for homing"
        else:
            print colored("Connect failed.",'red')
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
        state = "supply test"

        #smpsOff over idle current test
        #is over current for smps off with power on (smpsOffovercurrent)
        if board.testjig == "rambo":
            powerOn()
            time.sleep(0.1)
            if isOverCurrent(0.0):
                state = "board fail"
                #continue ??
            smpsOn() #get rdy for next smpsOn test

        #smpsOn over idle current test
        #is over idle current for mini and rambo
        if state != "board fail":
            powerOn()
            if isOverCurrent(board.thresholdCurrent):
                state = "board fail"
        if state == "board fail":
            print "Powering failed."

    elif state == "dryrunfullstep":
        state = "fullstep"
        if board.testjig == "disablerambodryrun":
          for drycount in range(40):
            print "DRYRUN " + str(drycount) + " Testing full step forward..."
            target.setMicroStepping(1)
            target.runSteppers(frequency = 200*stepperTestRPS, steps = 200,direction = target.UP, triggerPin = board.triggerPin, wait = False)
            controller.monitorSteppers(pin = monitorPin,frequency = monitorFrequency)
            print "DRYRUN " + str(drycount) + " Testing full step reverse..."
            target.runSteppers(frequency = 200*stepperTestRPS, steps = 200,direction = target.DOWN, triggerPin = board.triggerPin, wait = False)
            controller.monitorSteppers(pin = monitorPin,frequency = monitorFrequency)
            finished = target.waitForFinish(commands = 2, timeout = 2, clear = True)
            if -1 in testProcessor.fullStep or not finished:
                print "Monitoring failed."
                state = "board fail"
                break
            else:
                state = "fullstep"

    elif state == "fullstep":
        print "Setting VREF to " + str(board.targetVref)
	target.setMotorCurrent(board.targetVref) #EINSY RETRO
        print "Testing full step forward..."
        target.setMicroStepping(1)
        target.runSteppers(frequency = 200*stepperTestRPS, steps = 200, 
                           direction = target.UP, triggerPin = board.triggerPin, wait = False)
        testProcessor.fullStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing full step reverse..."
        target.runSteppers(frequency = 200*stepperTestRPS, steps = 200, 
                           direction = target.DOWN, triggerPin = board.triggerPin, wait = False)
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
                           direction = target.UP, triggerPin = board.triggerPin, wait = False)
        testProcessor.halfStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing half step reverse..."
        target.runSteppers(frequency = 400*stepperTestRPS, steps = 400, 
                           direction = target.DOWN, triggerPin = board.triggerPin, wait = False)
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
                           direction = target.UP, triggerPin = board.triggerPin, wait = False)
        testProcessor.quarterStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing quarter step reverse..."
        target.runSteppers(frequency = 800*stepperTestRPS, steps = 800, 
                           direction = target.DOWN, triggerPin = board.triggerPin, wait = False)
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
                           direction = target.UP, triggerPin = board.triggerPin, wait = False)
        testProcessor.sixteenthStep += controller.monitorSteppers(pin = monitorPin, 
                                                   frequency = monitorFrequency)
        print "Testing sixteeth step reverse..."
        target.runSteppers(frequency = 3200*stepperTestRPS, steps = 3200, 
                           direction = target.DOWN, triggerPin = board.triggerPin, wait = False)
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
        for pin in board.vrefPins:
            testProcessor.vrefs += controller.analogRead(pin)
        if -1 in testProcessor.vrefs:
            print "Reading references failed."
            state = "board fail"
        else:     
            state = "dryrunfullstep"
#            state = "fullstep"
#            state = "thermistors"
#            state = "processing"

    elif state == "supply test":
        #logic_voltage_reading = analog2volt(controller.analogRead(supplyPins[2]))
        #print "5V PIN READING: " + str(logic_voltage_reading)
        #if logic_voltage_reading <= 5.0:
        #    state = "board fail"
        #    continue
        state = "uploading"
        print "Testing supply voltages..."
        for pin in supplyPins:
            testProcessor.supplys += controller.analogRead(pin)
        if -1 in testProcessor.supplys:
            print "Reading supplies failed."
            state = "board fail"
            continue
        #
        # Minimum Voltage Test for Safe Programming (prevent overstress)
        #
        if analog2volt(testProcessor.supplys)[2] <= board.testProcessor.railsLow[2]:
            print "5V PIN READING: " + str(analog2volt(testProcessor.supplys)[2])
            print "ERROR: Not reading 5 volts. Not safe to continue."
            state = "board fail"


    elif state == "spiflashid":
        #state = "mosfet high"
        state = "program marlin"
        if board.testjig not in ["archim","einsyrambo"]: continue
        print "Testing SPI FLASH Chip by reading the ID..."
        testProcessor.spiflashid = target.initSpiflash()
        print colored(format(int(testProcessor.spiflashid[0]),"#x"), 'blue')
        if -1 in testProcessor.spiflashid:
            print "Reading SPI FLASH ID failed."
            state = "board fail"
            continue

        print "Testing SPI FLASH Chip by writing the number 42 then reading it back..."
        testProcessor.spiflashData = target.spiflashWriteRead(42)
        print colored(testProcessor.spiflashData, 'blue')
        if -1 in testProcessor.spiflashData:
            print "Reading spi flash data time out."
            state = "board fail"
            continue


        if board.testjig is not "archim": continue
        print "Testing Archim SDCARD."
        testProcessor.sdcard = target.initSdcard()
        if -1 in testProcessor.spiflashid:
            print "Reading SDCARD failed."
            state = "board fail"
            continue

    elif state == "i2c floating":
        state = "mosfet high"
        passed = True
        ehresults = []
	print "Testing i2c pins low..."
	for pin in board.I2CPins:
            passed = target.pinLow(pin)
            time.sleep(0.01)
            ehresults += target.readPin(pin)
            target.pullupReadPin(pin)
        print "names: " + str(["SDA", "SCL"])
        print "results: " + str(ehresults)
	if -1 in ehresults or not passed:
	    print "Reading i2c pins failed."
            state = "board fail"  
        if ehresults != [0,0]:
            print "I2C Pullup Test Failed (not [0,0]). Stopping Test."
            testProcessor.errors += "Check I2C"
            state = "board fail"

    elif state == "mosfet high":
        passed = True
        print "Testing MOSFETs high..."
        for pin in board.mosfetOutPins:
            passed &= target.pinHigh(pin)
        for pin in board.mosfetInPins:
            testProcessor.mosfetHigh += controller.pullupReadPin(pin)
            
        if -1 in testProcessor.mosfetHigh or not passed:
            print "Reading mosfets failed."
            state = "board fail"      
        else:     
            state = "mosfet low"

    elif state == "mosfet low":
        passed = True
        print "Testing MOSFETs low..."
        for pin in board.mosfetOutPins:
            passed &= target.pinLow(pin)
        for pin in board.mosfetInPins:
            testProcessor.mosfetLow += controller.pullupReadPin(pin)
        if -1 in testProcessor.mosfetLow or not passed:
            print "Reading mosfets failed."
            state = "board fail"      
        else:     
            state = "endstop high"

    elif state == "endstop high":
        if test_diags_high():
            state = "board fail"
            continue
        if test_diags0_low():
            state = "board fail"
            continue
        if test_diags1_low():
            state = "board fail"
            continue
        passed = True
        if board.testjig == "einsyretro":
            target.pinLow(53) #Drive SDCard Chip Select low to test the MISO buffer. The miso buffers enable pin is connected to SDSS
        if board.testjig == "einsyrambo":
            target.pinLow(77) #Drive SDCard Chip Select low to test the MISO buffer. The miso buffers enable pin is connected to SDSS
        print "Testing endstops high..."
        for pin in board.endstopOutPins:
            passed &= controller.pinHigh(pin)
        for pin in board.endstopInPins:
            testProcessor.endstopHigh += target.readPin(pin)
        if -1 in testProcessor.endstopHigh or not passed:
            print "Reading endstops failed."
            state = "board fail"      
        else:     
            state = "endstop low"

    elif state == "endstop low":
        passed = True
        print "Testing endstops low..."
        for pin in board.endstopOutPins:
            passed &= controller.pinLow(pin)
        for pin in board.endstopInPins:
            testProcessor.endstopLow += target.readPin(pin)
        if -1 in testProcessor.endstopLow or not passed:
            print "Reading endstops failed."
            state = "board fail"
        else:
            state = "vrefs"
        if board.testjig == "einsyretro":
            target.pinHigh(53) #Drive SDCard Chip Select High
        if board.testjig == "einsyrambo":
            target.pinHigh(77) #Drive SDCard Chip Select High

    elif state == "thermistors":
        print "Testing thermistor values..."
        for pin in board.thermistorPins:
            testProcessor.thermistors += target.analogRead(pin)
        if -1 in testProcessor.thermistors:
            print "Reading thermistors failed."
            state = "board fail"
        else:
            #state = "program marlin"
            state = "spiflashid"
            if isOverCurrent(board.motorEnabledThresholdCurrent): state = "board fail"
            targetMotorsDisable()
            time.sleep(1.5)
            if isOverCurrent(board.thresholdCurrent): state = "board fail"

    elif state == "program marlin":
        #flush any accidently preloaded inputs
        sys.stdin.flush()
        sys.stdout.flush()
        termios.tcflush(sys.stdin, termios.TCIOFLUSH)

        if bootloadOnlyMode == False:
            print "Disconnecting target from test server..."
            board.target.close()

        if board.testjig == "archim":
            state = board.programVendorFirmware()
            continue

        ##skip factory fw
        #state = "testamps"
        #continue

        print "Programming target with vendor firmware..."
        if avrdude.upload(board.vendorFirmware, timeout = 80):
            state = "testamps"
            #state = "processing"
        else:
            print "Upload failed!"
            state = "board fail"

    elif state == "testamps":
        state = "processing"
        if isOverCurrent(board.thresholdCurrent): state = "board fail"
        if state =="processing" and board.testjig =="rambo":
            smpsOff()
            if isOverCurrent(board.thresholdCurrent): state = "board fail"

    elif state == "processing":
        if testProcessor.verifyAllTests():
            call(["./tpgrep.sh",serialNumber])
            if bootloadOnlyMode == True:
                print colored(serialNumber + " Bootloader success!", 'green')
            else:
                print colored(serialNumber + " Board passed!", 'green')
            testProcessor.errors = "Passed" + testProcessor.errors
            tplog_msg = ' Passed\n'
            if bootloadOnlyMode == True:
                tplog_msg = " Btldr" + tplog_msg
            with open(logFile, "a") as tpLog:
                tpLog.write(serialNumber + tplog_msg)
            state = "finished"
        else:
            powerOff()
            call(["./tpgrep.sh",serialNumber])
            print colored(serialNumber + " Board failed!", 'red')
            testProcessor.errors = "Failed:" + testProcessor.errors
            with open(logFile, "a") as tpLog:
                tpLog.write(serialNumber + ' Failed\n')
            state = "enter code"
        if bootloadOnlyMode == True:
            testProcessor.errors = "Bootloader " + testProcessor.errors
        testProcessor.showErrors()
        
    elif state == "board fail":
        #powerOff()
        print "Unable to complete testing process!"
        print colored(serialNumber + " Board failed",'red')
        with open(logFile, "a") as tpLog:
            tpLog.write(serialNumber + ' Failed\n')
        testProcessor.verifyAllTests()
        testProcessor.showErrors()
        #powerOff()
        testProcessor.errors = "Failed:" + testProcessor.errors
        print "Restarting test controller..."
        controller.restart()
        if target.serial.isOpen():
            print "Closing target..."
            target.close()
        #state = "finished"
	state = "enter code"

    elif state == "enter code":
        #flush any accidently preloaded inputs
        #sys.stdin.flush()
        #sys.stdout.flush()
        #termios.tcflush(sys.stdin, termios.TCIOFLUSH)

        while True:
            powerOff()
            print "0 See Comments, 1 Valid Fail, 2 Board insertet incorrectly, 3 No Fuse, 4 Bootloader missing"
            print "Enter code for fail: "
            failCode = raw_input().strip()
            try:
                failCode = int(failCode)
                if failCode in range(0,4):
                    break
                else:
                    print "Invalid Entry."
                    call(["beep","-f 2250"])
            except:
                print "Invalid Entry."
                call(["beep","-f 2250"])

        if failCode == 0:
            print "Enter note for fail: "
            failNote = raw_input()
        state = "finished"
        
    elif state == "finished":
        powerOff()
        print "Writing results to database..."
        #cursor.execute("""INSERT INTO testdata(serial, timestamp, testresults, testversion, testdetails, failure_code, failure_notes) VALUES (%s, %s, %s, %s, %s, %s, %s)""", (serialNumber, 'now', testProcessor.errors, version, str(testProcessor.resultsDictionary()), failCode, failNote ))
        cursor.execute("""INSERT INTO testdata(serial, timestamp, testresults, testversion, testdetails, failure_code, failure_notes, wave_operator, qc, tester, amps, gitdiff, gitbranch, iserial, testjig, productionRunId, bootloader2560_filename, bootloader32u2_filename, board) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (serialNumber, 'now', testProcessor.errors, version, str(testProcessor.resultsDictionary()), failCode, failNote, waveOperator, qcPerson, testPerson, str(currentReadings), gitdiff, gitbranch, iserial, board.testjig, orderRunId, board.bootloader2560, board.firmware32u2, sys.argv[2] ))
	count = get_count_for_runid(orderRunId)
	cursor.execute("""UPDATE productionruns SET endqty=%s WHERE productionrunid=%s""",(count ,orderRunId))
        testStorage.commit()
        testProcessor.restart()
        print "Preparing Test Jig for next board..."
        powerOff()
        if board.testjig == "rambo":
            controller.home(homingRate, wait = True)
        controller.restart()
        state = "start" 
