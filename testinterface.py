import serial
import time
import os
import sys
import re
from watchpuppy import *

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
         
    def open(self, port):
        if not os.path.exists(port):
            print "Serial port not detected!"
            return False
        self.serial.port = port
        self.serial.open()
        self.serial.setDTR(0)
        time.sleep(1)
        self.serial.setDTR(1)
        
        self.watchPuppy.startWatching(timeout = 2)
        while not self.serial.inWaiting():
            time.sleep(0.1)
            if self.watchPuppy.timedOut(): 
                print "Could not initialize serial communication!"
                return False
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
         self.close()
         self.open(port = self.serial.port)
         
    def read(self):
        return self.serial.read(self.serial.inWaiting())
        
    def pinHigh(self, pin):
        self.read() # Clear output
        self.serial.write("W"+str(pin)+"H_")
        return self.waitForFinish(clear = True)
            
    def pinLow(self, pin):
        self.read() # Clear output        
        self.serial.write("W"+str(pin)+"L_")
        return self.waitForFinish(clear = True)
                      
    def setMicroStepping(self, level):
        self.read() # Clear output        
        self.serial.write("U"+str(level)+"_")
        return self.waitForFinish(clear = True)
                     
    def analogRead(self, pin): #Use Arduino analog pin numbering
        """Returns list with pin state"""
        self.read() # Clear output        
        self.serial.write("A"+str(pin)+"_")
        self.waitForFinish()
        if self.waitForFinish():
            return self._findValues()  
        else: 
            return [-1]
    
    def pullupReadPin(self, pin):
        """Returns list with pin state"""
        self.read() # Clear output        
        self.serial.write("Q"+str(pin)+"_")
        self.waitForFinish()
        if self.waitForFinish():
            return self._findValues()   
        else: 
            return [-1]   
 
    def readPin(self, pin):
        """Returns list with pin state"""
        self.read() # Clear output        
        self.serial.write("R"+str(pin)+"_")
        if self.waitForFinish():
            return self._findValues()
        else: 
            return [-1]
        
    def home(self, rate, wait = True):
        self.read() # Clear output
        self.serial.write("H"+str(rate)+"_")
        if wait:
            return self.waitForFinish(timeout = rate/1000, clear = True)
        else:
            return True
            
    def runSteppers(self, frequency = 0, steps = 0, direction = "D",
                    triggerPin = -1, wait = True):
        command = "C" + str(steps) + "F" + str(frequency) + direction
        if triggerPin > -1:
            command += "P" + str(triggerPin) + "_"
        self.serial.write(command)
        if wait:
            return self.waitForFinish(timeout = rate/1000, clear = True)
        else:
            return True
    
    #This is a highly atomic operation, we might need to fix.
    def monitorSteppers(self, pin = 0, frequency = 1000):
        self.serial.write("M"+str(pin)+"F"+str(frequency)+"_")
        if self.waitForFinish(timeout = 2):
            return self._findValues(groups = 5)
        else:
            return [-1]
        
              
    def waitForFinish(self, commands = 1, timeout = 1, clear = False):
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
    
    def waitForStart(self):
        while "start" not in self.output:
            self.output += self.read()       
        self.output = ""
        return True
        
    def _findValues(self, groups = 0):
        vals = []
        if groups > 0:
            vals = self._groupn(map(int,re.findall(r'\b\d+\b', self.output)), groups)
        else:
            vals = map(int,re.findall(r'\b\d+\b', self.output))  
        self.output = ""
        return vals
