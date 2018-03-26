
#based on testinterface.py
import serial
import time
import os
import sys
import re
from watchpuppy import *
from termcolor import colored

class DirectPSU():
    """A class to abstract away turning on/off a PSU and taking current measurement.""" 
    def __init__(self):
        self.overCurrentChecking = True;
        currentReadings = []
        self.controller = None
        self.powerPin = -1

    def open(self, port = "/dev/ttyUSB0"):
        return

    def showMeasuredCurrent(self): #show measured current
        for count in range(5):
            self.controller.analogRead(1)
        ampreadings=[]
        for count in range(20):
            ampreadings += self.controller.analogRead(1)
        amps = sum(ampreadings)/len(ampreadings) * (5.0/1024.0)
        print colored("measured current: " + str(amps) + " Amps",'blue',attrs=['bold'])

    def isOverCurrent(self,threshold):
        if not overCurrentChecking: 
            return False
        adcReadings = []

        time.sleep(0.1)
        for count in range(5):
            self.controller.analogRead(1)
        for count in range(20):
            adcReadings += self.controller.analogRead(1)
        meanAmps = round(sum(adcReadings)/len(adcReadings) * (5.0/1024.0),4)
        print colored("current_reading: " + str(meanAmps) + " Amps",'blue')
        self.currentReadings.append(meanAmps)

        if(meanAmps > threshold):
            powerOff()
            testProcessor.errors += "Over " + str(threshold) + " amps\n"
            print colored("Board is OVER MAXIMUM current threshold: " + str(threshold),'red')
            print colored("Check for reverse capacitor or short circuit...",'yellow')
            return True
        return False


    def on(self): #psu ON
        print("set psu on.")
        self.controller.pinHigh(powerPin)
        time.sleep(0.2)


    def off(self): #psu OFF
        print("set psu off.")
        self.controller.pinLow(powerPin)

    def sendline(self,cmd):
        return

    def close(self):
        return

    def readValue(self):
        return -1

    def read(self):
        return -1

