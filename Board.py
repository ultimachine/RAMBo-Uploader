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
    if iserial == 0:
        print colored("USB internal serial number not found.","yellow")
    return iserial

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

'''
  This class defines characteristics that are specific to the Rambo.  It inherits
  all qualities from the Board class
'''
class Rambo(Board):

  def __init__(self):
    self.triggerPin = 3
    self.testFirmwarePath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
    self.vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
    self.vrefPins = [8, 6, 5, 4, 3] #x, y, z, e0, e1 on controller
    self.mosfetOutPins = [9, 8, 7, 6, 3, 2] #On target
    self.mosfetInPins = [44, 32, 45, 31, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
    self.thermistorPins = [0, 1, 2, 7]
    self.setTestFirmware()
    self.setVendorFirmware()
    self.thresholdCurrent = 0.023
    self.id = 1
    self.testjig = "rambo"
    self.motorEnabledThresholdCurrent = 1.45
    self.setVendorFirmware()
    self.setTestFirmware()
    self.setTestProcessor()

  '''
  Method that sets the state to clamping for the Rambo testjig
  '''
  def setState(self):
    return "clamping"

'''
  This class defines characteristics that are specific to the MiniRambo.  It inherits
  all qualities from the Board class
'''
class MiniRambo(Board):

  def __init__(self):
    self.triggerPin = 4
    self.testFirmwarePath = "/home/ultimachine/workspace/MiniRamboTestJigFirmware/target_test_firmware.hex"
    self.vendorFirmwarePath = "/home/ultimachine/workspace/johnnyr/Mini-Rambo-Marlin/Marlin.cpp.hex"
    self.vrefPins = [6, 5, 4,] #x, y, z, e0, e1 on controller
    self.mosfetOutPins = [3, 6, 8, 4] #On target
    self.mosfetInPins = [44, 45, 46, 30] #On controller [PL5,PC5,PL4,PC6,PL3,PC7]
    self.thermistorPins = [0, 1, 2]
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
    self.testProcessor.thermistorLow = 925
    self.testProcessor.thermistorHigh = 955

  '''
  This method is made so that the clamping state is skipped in the test program
  '''
  def setState(self):
    return "powering"



