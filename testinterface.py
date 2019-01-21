import serial
import time
import os
import sys
import re
from watchpuppy import *
from termcolor import colored

def listports():
	import glob
	print(' '.join( glob.glob("/dev/ttyACM[0-9]") )) #effectively 'ls /dev/ttyACM*'

class TestInterface():
    """A class to abstract away serial handling and communication with 
       board running the test firmware.""" 
    def __init__(self):
        self.serial = serial.Serial(port = None, baudrate = 115200)
        self.watchPuppy = WatchPuppy()
        self.UP = "U"
        self.DOWN = "D"
        self.output = ""
        self._groupn = lambda lst, sz: [lst[i:i+sz] for i in range(0, len(lst), sz)]
        self.debugmode = False
        self.writeColor = 'magenta'
        self.writeAttrs = []
        self.responseColor = 'yellow'
        self.responseAttrs = []
         
    def open(self, port):
        if not os.path.exists(port):
            print "Serial port not detected!"
            listports()
            while(1):
                time.sleep(1)
            return False
        self.serial.port = port
        self.serial.open()
        self.serial.flushOutput()
        #self.serial.flushInput()
        #self.serial.setDTR(0)
        #time.sleep(1)
        #self.serial.setDTR(1)
        
        self.watchPuppy.startWatching(timeout = 2)
        while self.serial.inWaiting() == 0:
            time.sleep(0.1)
            if self.watchPuppy.timedOut(): 
                print "Could not initialize serial communication!"
                self.serial.close()
                return False
        time.sleep(1)
        print "Successfully connected to " + self.serial.port + " at " \
               + str(self.serial.baudrate) + " baud..."
        self.read() #Clear output
        self.output = ""
        return True

    def close(self):
        if self.serial.port is not None:
            self.serial.close()
        return True
    
    def restart(self):
        self.serial.setDTR(0)
        self.serial.setDTR(1)
        self.serial.flushOutput()
        self.serial.flushInput()
         
    def read(self):
        return self.serial.read(self.serial.inWaiting())

    def write(self, cmd):
        if(self.debugmode): print( colored(cmd, self.writeColor, attrs=self.writeAttrs) )
        self.serial.write(cmd)
        
    def pinHigh(self, pin):
        self.write("W"+str(pin)+"H_")
        return self.waitForFinish(clear = True)
            
    def pinLow(self, pin):
        cmd = "W"+str(pin)+"L_"
        #if(self.debugmode): print colored(cmd,'magenta')
        self.write(cmd)
        return self.waitForFinish(clear = True)
                      
    def setMicroStepping(self, level):
        self.write("U"+str(level)+"_")
        return self.waitForFinish(clear = True)

    def setMotorCurrent(self, level):
        self.write("V"+str(level)+"_")
        return self.waitForFinish(clear = True)
                     
    def analogRead(self, pin): #Use Arduino analog pin numbering
        """Returns list with pin state"""
        self.write("A"+str(pin)+"_")
        if self.waitForFinish():
            return self._findValues()  
        else: 
            return [-1]

    def initSpiflash(self):
        """Returns archim spiflash mfg id"""
        self.write("S_")
        if self.waitForFinish():
            return self._findValues()
        else:
            return [-1]

    def spiflashWriteRead(self, value): #Write SPIFLASH then READ it's value to verify
        """Returns list with pin state"""
        self.write("S"+str(value)+"_")
        if self.waitForFinish():
            return self._findValues() 
        else:
            return [-1]

    def initSdcard(self):
        """Returns archim spiflash mfg id"""
        self.write("D_")
        if self.waitForFinish(timeout=7):
            return self._findValues()
        else:
            return [-1]

    #driveMode options
    #driveMode = 0 sets diag0 to push_pull
    #driveMode = 1 sets diag1 to push_pull
    #driveMode = 2 sets both back to open drain
    ####REMOVED pin = chip select for the driver to set
    def set_trinamic_diag_mode(self, driveMode=2):
        """Program the Trinamic TMC2130 Diag outputs"""
        self.write("T"+str(driveMode)+"_") #"P"+str(pin)+
        if self.waitForFinish():
            return self._findValues()
        else:
            return [-1]

    def pullupReadPin(self, pin, timeout = 2):
        """Returns list with pin state"""
        self.write("Q"+str(pin)+"_")
        if self.waitForFinish(timeout=timeout):
            return self._findValues()   
        else: 
            return [-1]   
 
    def readPin(self, pin):
        """Returns list with pin state"""
        self.write("R"+str(pin)+"_")
        if self.waitForFinish():
            return self._findValues()
        else: 
            return [-1]
        
    def home(self, rate, wait = True):
        self.write("H"+str(rate)+"_")
        if wait:
            return self.waitForFinish(timeout = rate/1000, clear = True)
        else:
            return True
            
    def runSteppers(self, frequency = 0, steps = 0, direction = "D",
                    triggerPin = -1, wait = True):
        command = "C" + str(steps) + "F" + str(frequency) + direction
        if triggerPin > -1:
            command += "P" + str(triggerPin) + "_"
        #if(self.debugmode): print colored(command,'magenta')
        self.write(command)
        if wait:
            return self.waitForFinish(timeout = frequency/1000, clear = True)
        else:
            return True
    
    #This is a highly atomic operation, we might need to fix.
    def monitorSteppers(self, pin = 0, frequency = 1000):
        self.write("M"+str(pin)+"F"+str(frequency)+"_")
        if self.waitForFinish(timeout = 2):
            return self._findValues(groups = 5)
        else:
            return [-1]
        
              
    def waitForFinish(self, commands = 1, timeout = 2, clear = False):
        self.watchPuppy.startWatching(timeout = timeout)
        while self.output.count("ok") < commands:
            self.output += self.read()
            if self.watchPuppy.timedOut():
                print "Response timed out!"
                if clear:
                    self.output = ""
                return False
        if clear:
            self.output = ""
        return True

    def flush(self):
        self.serial.flushInput() #flush host input
        self.output = ""
    
    def waitForStart(self):
        self.serial.flushInput() #flush host input
        self.output = ""
        while "start" not in self.output:
            time.sleep(0.1)
            self.output += self.read()
        self.output = ""
        return True
        
    def _findValues(self, groups = 0):
        vals = []
        if groups > 0:
            vals = self._groupn(map(int,re.findall(r'\b\d+\b', self.output)), groups)
        else:
            vals = map(int,re.findall(r'\b\d+\b', self.output))  
        if self.debugmode:
            print( colored(self.output,self.responseColor,attrs=self.responseAttrs) )
        self.output = ""
        self.read()
        return vals
