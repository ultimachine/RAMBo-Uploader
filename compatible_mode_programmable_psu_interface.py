
#based on testinterface.py
#Controls an HP 6633A Power Supply using "Compatible Mode"

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

class CompatProgrammablePSU():
    def __init__(self):
        self.status = ""
        self.retry_count = 0

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
            print " port=" + str(port)
            #listports()
            #while(1):
            #    time.sleep(1)
            return False
        self.serial.port = port
        self.serial.open()
        self.serial.flushOutput()
        self.serial.flushInput()

        self.sendquery(b'++eot_enable 0')
        self.sendquery(b'++auto 0')
        self.sendquery(b'++addr 5')
        self.sendquery(b'ID?')

        self.watchPuppy.startWatching(timeout = 2)
        while self.serial.inWaiting() == 0:
            time.sleep(1.1)
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
        print("show set voltage: not supported")

    def showSetCurrent(self): #show set current
        print("show set current: not supported")

    def showMeasuredCurrent(self): #show measured current
        sys.stdout.write("measured current: ")
        self.sendquery(b'IOUT?')
        print colored(self.readValue(),'blue',attrs=['bold'])

    def showStatus(self): #show measured current
        sys.stdout.write("STS?: ")
        self.sendquery(b'STS?')
        self.status = self.read().strip()
        print colored(self.status,'blue',attrs=['bold'])

    def program_psu_settings(self): #comments show SCPI commands
        self.sendline(b'OUT 0') #:OUTPUT OFF
        self.sendline(b'RST') #:SOURCE:CURRENT:PROTECTION:CLEAR
        #:OUTPUT:OCP:VALUE 2
        self.sendline(b'OCP 1') #:OUTPUT:OCP ON
        #:OUTPUT:OVP:VALUE 25
        #:OUTPUT:OVP ON
        self.sendline(b'VSET 24') #:APPLY CH1,24,2
        self.sendline(b'ISET 2.0') #:APPLY CH1,24,2

    def on(self): #psu ON
        print("set psu on.")
        self.program_psu_settings()
        self.sendline(b'OUT 1') #:OUTPUT ON
        time.sleep(1) #0.2
        self.showStatus();
        
        if(self.status == "1216" and self.retry_count < 5):
            self.retry_count = self.retry_count + 1
            self.on()


    def off(self): #psu OFF
        print("set psu off.")
        self.retry_count = 0
        self.sendline(b'OUT 0') #:OUTPUT OFF

    def sendline(self,cmd):
        self.serial.flushInput()
        self.serial.write(cmd + '\n')
        #time.sleep(0.2)

    def sendquery(self,cmd):
        self.serial.flushInput()
        self.serial.write(cmd + '\n')
        time.sleep(0.1)
        #self.serial.write("++read eoi" + '\n')
        self.serial.write(b"++read eoi\n")
        time.sleep(0.2)

    def close(self):
        if self.serial.port is not None:
            self.serial.close()
        return True

    def readValue(self):
        if self.waitForFinish(timeout = 1): #0.5
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
