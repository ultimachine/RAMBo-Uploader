#!/usr/bin/env python

'''
  This class defines all the general characteristics of ultimachine
  Boards.
'''

from testprocessor import *
from avrdude import *
from atmega import *
from testinterface import *
import shlex
import time

class Board:
  global triggerPin
  global vendorFirmwarePath
  global vrefPins
  global mosfetOutPins
  global mosfetInPins
  global thermistorPins
  global testProcessor
  global thresholdCurrent
  global iserial
  global testProcessor
  global id
  global testjig

  def __init__(self):
    self.motorEnablePins = []
    self.vrefPins = []
    self.controller = TestInterface()
    self.target = TestInterface()

  '''
    A function that initializes a testProcessor object
  '''
  def setTestProcessor(self):
    self.testProcessor = TestProcessor()

  '''
    Method to retrieve CPU serial number
    @port Which port the board is connected to
  '''
  def setISerial(self, port):
    targetPort = port
    iserial = 0
    #/sbin/udevadm info --query=property --name=/dev/ttyACM1 | awk -F'=' '/SHORT/ {print $2}
    #for line in subprocess.check_output(shlex.split("/sbin/udevadm info --query=property --name=/dev/ttyACM1")).splitlines():
    iserialproc = subprocess.Popen(shlex.split("/sbin/udevadm info --query=property --name=" + targetPort),stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in iserialproc.communicate()[0].splitlines():
      if line.split('=')[0] == "ID_SERIAL_SHORT": iserial = line.split('=')[1]
    #if iserial == 0:
    #    print colored("USB internal serial number not found.","yellow")
    #return iserial

  '''
    A method that initializes an ATmega object and defines the processor and
    and firmware file path for testing
  '''
  def setTestFirmware(self):
    self.testFirmware = Atmega()
    self.testFirmware.name = "atmega2560"
    self.testFirmware.bootloader = self.testFirmwarePath

  '''
    A method that initializes an ATmega object and defines the processor and
    and firmware file path for vendor
  '''
  def setVendorFirmware(self):
    self.vendorFirmware = Atmega()
    self.vendorFirmware.name = "atmega2560"
    self.vendorFirmware.bootloader = self.vendorFirmwarePath

  def disableMotors(self):
                 for enablePin in self.motorEnablePins:
                      self.target.pinHigh(enablePin)

'''
  This class defines characteristics that are specific to the Rambo.  It inherits
  all qualities from the Board class
'''
class Rambo(Board):

  def __init__(self):
    Board.__init__(self)

    self.triggerPin = 3
    self.testFirmwarePath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
    self.vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
    self.vrefPins = [8, 6, 5, 4, 3] #x, y, z, e0, e1 on controller
    #self.mosfetNames = ["Bed","Fan2","Fan1","Heat1","Fan0","Heat0"]
    self.mosfetOutPins = [9, 8, 7, 6, 3, 2] #On target
    self.mosfetInPins = [44, 32, 45, 31, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
    self.endstopOutPins = [83, 82, 81, 80, 79, 78] #controller outputs
    self.endstopInPins = [12, 11, 10, 24, 23, 30] #target inputs
    self.thermistorPins = [0, 1, 2, 7]
    self.motorEnablePins = [29,28,27,26,25]
    self.thresholdCurrent = 0.02
    self.motorEnabledThresholdCurrent = 1.4
    self.id = 1
    self.testjig = "rambo"
    self.setVendorFirmware()
    self.setTestFirmware()
    self.setTestProcessor()

  '''
  Method that sets the state to clamping for the Rambo testjig
  '''
  def setState(self):
    #return "clamping"
    #skip clamping for bench test of rambo
    return "powering"

'''
  This class defines characteristics that are specific to the MiniRambo.  It inherits
  all qualities from the Board class
'''
class MiniRambo(Board):

  def __init__(self):
    Board.__init__(self)
    self.vrefPins = []

    self.triggerPin = 4
    self.testFirmwarePath = "/home/ultimachine/workspace/MiniRamboTestJigFirmware/target_test_firmware.hex"
    self.vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Mini-Rambo-Marlin/Marlin.cpp.hex"
    #self.vrefPins = [6, 5, 4,] #x, y, z, e0, e1 on controller
    #self.mosfetNames = ["Bed","Fan2","Fan1","Heat1","Fan0","Heat0"]
    self.mosfetOutPins = [3, 6, 8, 4] #On target
    self.mosfetInPins = [44, 45, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
    #self.endstopNames = ["X min", "Y min", "Z min", "X max", "Y max", "Z max"]
    self.endstopOutPins = [83, 82, 81, 80, 79, 78] #controller outputs
    self.endstopInPins = [12, 11, 10, 24, 23, 30] #target inputs
    self.thermistorPins = [0, 1, 2]
    self.motorEnablePins = [29,28,27,26]
    self.thresholdCurrent = 0.017
    self.motorEnabledThresholdCurrent = 1.05
    self.id = 2
    self.testjig = "minirambo"
    self.setTestProcessor()
    self.setTestFirmware()
    self.setVendorFirmware()

  '''
  The TestProcessor class initializes all variables to Rambo settings.  This method
  overrides those variables for the minirambo
  '''
  def setTestProcessor(self):
    self.testProcessor = TestProcessor()
    self.testProcessor.axisNames = ["X","Y","Z","E0"] #no E1
    self.testProcessor.vrefNames = ["X,Y","Z","E0"]
    self.testProcessor.thermistorNames = ["T0","T1","T2"] #no T3
    self.testProcessor.mosfetNames = ["Bed","Fan1","Fan0","Heat0"]
    #self.testProcessor.thermistorLow = 925
    #self.testProcessor.thermistorHigh = 955

  '''
  This method is made so that the clamping state is skipped in the test program
  '''
  def setState(self):
    return "powering"

class EinsyRambo(MiniRambo):
  def __init__(self):
    MiniRambo.__init__(self)
    self.testFirmwarePath = "/home/ultimachine/workspace/Einsy/Test_Jig_Firmware/Test_Jig_Firmware.ino.rambo.hex"
    #self.vendorFirmwarePath = "/home/ultimachine/workspace/RAMBo-Uploader/PrusaFirmware.einsy.hex"
    self.vendorFirmwarePath = "/home/ultimachine/workspace/Einsy/Marlin/Marlin/Marlin.ino.rambo.hex"
    self.setVendorFirmware()
    self.setTestFirmware()
    self.testjig = "einsyrambo"
    self.thresholdCurrent = 0.085
    self.thermistorPins = [0, 1, 2, 3, 6]
    self.endstopOutPins = [83, 82, 81 ] #controller outputs
    self.endstopInPins = [12, 11, 10 ] #target inputs
    self.testProcessor.thermistorNames = ["T0","T1","T2","ZTHERM","BTHERM"]

class PrusaEinsy(EinsyRambo):
  def __init__(self):
    EinsyRambo.__init__(self)
    #self.vendorFirmwarePath = "/home/ultimachine/workspace/RAMBo-Uploader/PrusaFirmware.einsy.hex"
    #self.vendorFirmwarePath = "/home/ultimachine/workspace/Einsy/Marlin/Marlin/Marlin.ino.rambo.hex"
    self.vendorFirmwarePath = "/home/ultimachine/Arduino/Blink/Blink.ino.rambo.hex"
    self.setVendorFirmware()
    self.firmware32u2 = "/home/ultimachine/Prusa-usbserial-DFU.hex"
    self.bootloader2560 = "/home/ultimachine/workspace/Einsy/stk500v2-prusa/stk500v2-prusa.hex"

class UltimachineEinsy(EinsyRambo):
  def __init__(self):
    EinsyRambo.__init__(self)
    self.vendorFirmwarePath = "/home/ultimachine/workspace/Einsy/Marlin/Marlin/Marlin.ino.rambo.hex"
    self.setVendorFirmware()
    self.firmware32u2 = "/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX"
    self.bootloader2560 = "/home/ultimachine/workspace/RAMBo-Uploader/stk500boot_v2_mega2560.hex"

class ArchimRambo(Board):
  def __init__(self):
    Board.__init__(self)

    #self.target.serial.baudrate = 1200

    #controller pins on rambo
    self.mosfetInPins = [44, 32, 45, 31, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
    self.endstopOutPins = [83, 82, 81, 80, 79, 78] #controller outputs
    #self.vrefPins = [8, 6, 5, 4, 3] #x, y, z, e0, e1 on controller

    self.resetPin = 84

    #target board pins (test points)
    self.triggerPin = 9 #7
    self.endstopInPins = [14, 29, 31, 32, 15, 30] #target inputs Xmin,Ymin,Zmin,Xmax,Ymax,Zmax
    self.mosfetOutPins = [9, 4, 8, 7, 6, 5] #On target BED, FAN0, HEAT3, HEAT2, HEAT1, FAN1
    self.testFirmwarePath = "archim_testfw.bin"
    self.vendorFirmwarePath = "archim_marlin.bin"
    self.thermistorPins = [10,9,11,8] #T0 T1 T2 T3
    self.motorEnablePins = [41,48,96,97,28] #X,Y,Z,E0,E1 PC9,PC15,PC10,PB24,PD3
    self.id = 3 #default run id for archim
    self.testjig = "archim"
    self.thresholdCurrent = 0.055
    self.motorEnabledThresholdCurrent = 1.05
    self.setTestProcessor()

  def setTestProcessor(self):
    self.testProcessor = TestProcessor()
    self.testProcessor.supplyNames = ["3V rail","Bed rail", "5V rail"]
    #self.testProcessor.thermistorLow = 925
    #self.testProcessor.thermistorHigh = 955
    self.testProcessor.rail_0_low = 3.22 #3.3 on MM reads 3.273 on test
    self.testProcessor.rail_0_high = 3.35
    self.testProcessor.railsLow = [3.22, 23, 4.7]
    self.testProcessor.railsHigh = [3.35, 25.5, 5.2]
    print "setting supply names: " + str(self.testProcessor.supplyNames)

  def setState(self):
    return "powering"
    return "supply test"
    #return "thermistors"
    return "connecting target"
    return "fullstep"

  def programTestFirmware(self):
        self.samba_mode()
        subprocess.Popen( shlex.split( "lsusb -d 27b1:0001" )).wait()
        program_testfw_cmd = 'bossac -e -w -v -b -R Test_Jig_Firmware.ino.archim.bin'
        program_testfw__process = subprocess.Popen( shlex.split( program_testfw_cmd ) )
        if program_testfw__process.wait():
                print colored("Uploading Test Firmware Failed.",'red')
                return "board fail"
        else:
                print colored("Uploading Test Firmware Success! ",'green')
                #time.sleep(1)
                #self.toggle_nrst()
                time.sleep(3)
                return "connecting target"

  def programVendorFirmware(self):
        #return "testamps"
        self.samba_mode()
        program_fw_cmd = 'bossac -e -w -v -b Marlin.ino.archim.bin'
        program_fw_process = subprocess.Popen( shlex.split( program_fw_cmd ) )
        if program_fw_process.wait():
                print colored("Uploading Vendor Firmware Failed.",'red')
                return "board fail"
        else:
                print colored("Uploading Vendor Firmware Success! ",'green')
                #self.toggle_nrst()
                #time.sleep(1)
                return "testamps"

  def toggle_nrst(self):
    print "toggle_reset"
    self.controller.pinHigh(9) #Rambo Heat0
    time.sleep(0.1)
    self.controller.pinLow(9)
    #self.controller.pinLow(84) #PH2 Rambo-EXT2-8
    #self.controller.readPin(84)

  def samba_mode2(self):
    import serial
    s = serial.Serial(port = "/dev/ttyACM1", baudrate = 1200)
    try:
        s.open()
        print "Target did not close USB and force SAMBA-mode after setting baud to 1200."
        s.close()
    except:
        print "SAMBA-mode."
        s.close()
    time.sleep(1)

  def samba_mode3(self):
	import serial
	s = serial.Serial(port = "/dev/ttyACM1", baudrate = 1200)
	try:
		s.open()
		print "Target did not close USB and force SAMBA-mode after setting baud to 1200."
		s.close()
	except:
		print "SAMBA-mode."
		s.close()

  def samba_mode(self):
	#subprocess.Popen( shlex.split( "/home/rig/btmode.py" )).wait()
	#return
	if not subprocess.Popen( shlex.split( "lsusb -d 03eb:6124" )).wait(): #look for samba boot loader
		print colored("Already in SAMBA mode.",'blue')
		return
	import serial
	import traceback
	import time
	s = serial.Serial(port = None, baudrate = 1200)
	try:
		s.port = "/dev/ttyACM1"
		if s.isOpen(): s.close()
		s.open()
		s.setDTR(0)
		#time.sleep(1)
		#s.setDTR(1)
		#s.close()
		print "Target did not close connection automatically."
	except IOError:
		print "Target closed connection automatically."
	except:
		traceback.print_exc()
	if s.isOpen(): s.close()
	time.sleep(1)
	if subprocess.Popen( shlex.split( "lsusb -d 03eb:6124" )).wait(): #look for samba boot loader
		print colored("SAMBA boot loader not found!",'red')
