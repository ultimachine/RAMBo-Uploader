
#based on testinterface.py
import serial
import time
import os
import sys
import re
from watchpuppy import *
from termcolor import colored

class ProgrammablePSU():
    """A class to abstract away serial handling and communication with a prorgrammable PSU.""" 
    def __init__(self):
        self.serial = serial.Serial(port = None, baudrate = 9600)
        self.watchPuppy = WatchPuppy()
        self.output = ""
        self._groupn = lambda lst, sz: [lst[i:i+sz] for i in range(0, len(lst), sz)]
        self.debugmode = True

        self.overCurrentChecking = True;

    def open(self, port = "/dev/ttyUSB0"):
        if not os.path.exists(port):
            print "Serial port not detected!"
            listports()
            while(1):
                time.sleep(1)
            return False
        self.serial.port = port
        self.serial.open()
        self.serial.flushOutput()
        self.serial.flushInput()

        self.serial.write(b'*IDN?\n')

        self.watchPuppy.startWatching(timeout = 2)
        while self.serial.inWaiting() == 0:
            time.sleep(0.1)
            if self.watchPuppy.timedOut(): 
                print "Could not initialize PSU communication!"
                return False
        time.sleep(1)
        print "Successfully connected to PSU on " + self.serial.port + " at " \
               + str(self.serial.baudrate) + " baud..."
        print colored(self.read(),'blue',attrs=['bold']) #Clear output

        self.program_psu_settings()

        self.output = ""
        return True

    def showSetVoltage(self): #show set voltage
        sys.stdout.write("set voltage: ")
        self.sendline(b':VOLTAGE?')
        print colored(self.read(),'blue',attrs=['bold'])

    def showSetCurrent(self): #show set current
        sys.stdout.write("set current: ")
        self.sendline(b':CURRENT?')
        print colored(self.read(),'blue',attrs=['bold'])

    def showMeasuredCurrent(self): #show measured current
        sys.stdout.write("measured current: ")
        self.sendline(b':MEASURE:CURRENT?')
        print colored(self.readValue(),'blue',attrs=['bold'])

    def program_psu_settings(self):
        self.sendline(b':OUTPUT OFF')
        self.sendline(b':SOURCE:CURRENT:PROTECTION:CLEAR')
        #self.sendline(b':OUTPUT:OCP:VALUE 2')
        #self.sendline(b':OUTPUT:OCP ON')
        self.sendline(b':OUTPUT:OVP:VALUE 25')
        self.sendline(b':OUTPUT:OVP ON')
        self.sendline(b':APPLY CH1,24,2')

    def on(self): #psu ON
        print("set psu on.")
        self.program_psu_settings()
        self.sendline(b':OUTPUT ON')
        time.sleep(0.2)


    def off(self): #psu OFF
        print("set psu off.")
        self.sendline(b':OUTPUT OFF')

    def sendline(self,cmd):
        self.serial.flushInput()
        self.serial.write(cmd + '\n')
        time.sleep(0.1)

    def close(self):
        if self.serial.port is not None:
            self.serial.close()
        return True

    def readValue(self):
        if self.waitForFinish(timeout = 2):
            return self.read()
        else: 
            return -1

    def read(self):
        return self.serial.read(self.serial.inWaiting())

    def _findValues(self, groups = 0):
        vals = []
        if groups > 0:
            vals = self._groupn(map(int,re.findall(r'\b\d+\b', self.output)), groups)
        else:
            vals = map(int,re.findall(r'\b\d+\b', self.output))  
        self.output = ""
        self.read()
        return vals

    def waitForFinish(self, commands = 1, timeout = 1, clear = False):
        self.watchPuppy.startWatching(timeout = timeout)
        while self.output.count('\n') < commands:
            self.output += self.read()
            if self.watchPuppy.timedOut():
                print "\nResponse timed out!"
                if clear:
                    self.output = ""
                return False
        if clear:
            self.output = ""
        return True
