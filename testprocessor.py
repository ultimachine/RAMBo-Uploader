from __future__ import division
from termcolor import colored

class TestProcessor():
    def __init__(self):
        self.fullStep = []
        self.halfStep = []
        self.quarterStep = []
        self.sixteenthStep = []
        self.vrefs = []
        self.supplys = []
        self.supplyVoltages = []
        self.mosfetHigh = []
        self.mosfetLow = []
        self.endstopHigh = []
        self.endstopLow = []
        self.thermistors = []
        self.spiflashid = []
        self.sdcard = []
        self.errors = ""
        self.failedAxes = [False,False,False,False,False]
        self.failedMosfets = [False,False,False,False,False,False]
        self.failedEndstops = [False,False,False,False,False,False]
        self.axisNames = ["X","Y","Z","E0","E1"]
        self.vrefNames = ["X","Y","Z","E0","E1"]
        self.thermistorNames = ["T0","T1","T2","T3"]
        self.supplyNames = ["Extruder rail","Bed rail", "5V rail"]
        self.mosfetNames = ["Bed","Fan2","Fan1","Heat1","Fan0","Heat0"]  
        self.endstopNames = ["X min", "Y min", "Z min", "X max", "Y max", "Z max"]
        self.thermistorLow = 956
        self.thermistorHigh = 987
        self.railsLow = [23, 23, 4.7]
        self.railsHigh = [25.5, 25.5, 5.2]


    def testSpiflashid(self):
        passed = True
        if self._wasTimedOut(self.supplys):
            print "...Timed out at Archim SPI FLASH ID test"
            return False

        for i in self.spiflashid:
            if (i == 20):
                pass
            else:
                self.errors += "Check SpiFlash.\n"
                passed &= False
        return passed

    def testSdcard(self):
        passed = True
        if self._wasTimedOut(self.supplys):
            print "...Timed out at Archim SDCARD init test"
            return False

        for i in self.sdcard:
            if (i == 42):
                pass
            else:
                self.errors += "Check SDCARD.\n"
                passed &= False
        return passed

    def testVrefs(self):
        passed = True
        if self._wasTimedOut(self.vrefs):
            print "...Timed out at vref test"
            return False
        for idx, val in enumerate(self.vrefs):
            if not 162 <= val <= 192:
                self.errors += self.vrefNames[idx] + " axis vref incorrect\n"
                passed &= False
        if max(self.vrefs) - min(self.vrefs) >= 16:
            self.errors +=  "Vref variance too high!\n"
            passed &= False
        return passed

    def testSupplys(self):
        passed = True
        if self._wasTimedOut(self.supplys):
            print "...Timed out at supply test"
            return False

        for i in [0,2]:
            if (self.railsLow[i] <= self.supplyVoltages[i] <= self.railsHigh[i]):
                pass
            else:
                self.errors += "Test " + self.supplyNames[i] + " supply\n"
                passed &= False

        return passed

    def testThermistors(self):
        passed = True
        if self._wasTimedOut(self.thermistors):
            print "...Timed out at thermistor test"
            return False
        for idx, val in enumerate(self.thermistors):
            if not self.thermistorLow <= val <= self.thermistorHigh:
                self.errors += "Check Thermistor " + self.thermistorNames[idx] + "\n"
                passed = False
        return passed

    def testMosfetLow(self):
        passed = True
        if self._wasTimedOut(self.mosfetLow):
            print "...Timed out at MOSFET low test"
            return False
        for idx, val in enumerate(self.mosfetLow):
            if not val == 1 and not self.failedMosfets[idx]:
                self.errors += "Check " + self.mosfetNames[idx] + " MOSFET\n"
                self.failedMosfets[idx] = True
                passed = False
        return passed

    def testMosfetHigh(self):
        passed = True
        if self._wasTimedOut(self.mosfetHigh):
            print "...Timed out at MOSFET high test"
            return False
        for idx, val in enumerate(self.mosfetHigh):
            if not val == 0 and not self.failedMosfets[idx]:
                self.errors += "Check " + self.mosfetNames[idx] + " MOSFET\n"
                self.failedMosfets[idx] = True
                passed = False
        return passed

    def testEndstopHigh(self):
        passed = True
        if self._wasTimedOut(self.endstopHigh):
            print "...Timed out at endstop high test"
            return False
        for idx, val in enumerate(self.endstopHigh):
            if not val == 1 and not self.failedEndstops[idx]:
                self.errors += "Check " + self.endstopNames[idx] + " endstop\n"
                self.failedEndstops[idx] = True
                passed = False
        return passed

    def testEndstopLow(self):
        passed = True
        if self._wasTimedOut(self.endstopLow):
            print "...Timed out at endstop low test"
            return False
        for idx, val in enumerate(self.endstopLow):
            if not val == 0 and not self.failedEndstops[idx]:
                self.errors += "Check " + self.endstopNames[idx] + " endstop\n"
                self.failedEndstops[idx] = True
                passed = False
        return passed

    def testStepperResults(self, vals):
        passed = True
        if self._wasTimedOut(vals):
            print "...Timed out at stepper test"
            return False
        for i in range(len(self.axisNames)): #Iterate over each stepper
            forward = vals[i] #Forward value are the first 5 in the list
            reverse = vals[i+5] #Reverse are the last 5
            print "Forward -> " + str(forward) + "Reverse -> " + str(reverse)
            for j in range(5): #Iterates over each entry in the test list
                #Here we fold the recording values onto each other and make sure
                #each residency time in a flag section is within +- 10 for
                #the forward and reverse segments
                validRange = range(reverse[4-j]-10,reverse[4-j]+10)
                if forward[j] not in validRange and not self.failedAxes[i]:
                    self.errors += "Check "+self.axisNames[i]+" stepper\n"
                    self.failedAxes[i] = True
                    passed = False
        return passed
        
    def verifyAllTests(self):
        passed = True
        
        if self.supplys: #Just realized this is spelled wrong
            print "Supply voltage values..."
            print str(self.supplyNames)
            print "ADC = " + str(self.supplys)
            self._analogToVoltage(readings = self.supplys)
            print self.supplyVoltages
            passed &= self.testSupplys()

        if self.vrefs:
            print "Vref values..."
            print self.vrefs
            passed &= self.testVrefs()

        if self.thermistors:
            #print "thermistor names"
            #print self.thermistorNames
            print "Target thermistor readings..."
            print self.thermistors
            passed &= self.testThermistors()

        if self.mosfetHigh:
            print "Mosfet high values..."
            print self.mosfetNames
            print self.mosfetHigh
            passed &= self.testMosfetHigh()

        if self.mosfetLow:
            print "Mosfet low values..."
            print self.mosfetLow
            passed &= self.testMosfetLow()

        if self.endstopHigh:
            print "Endstop high values..."
            print self.endstopHigh
            passed &= self.testEndstopHigh()

        if self.endstopLow:
            print "Endstop low values..."
            print self.endstopLow
            passed &= self.testEndstopLow()

        if self.fullStep:
            print "Full step results"
            passed &= self.testStepperResults(self.fullStep)

        if self.halfStep:
            print "Half step results"
            passed &= self.testStepperResults(self.halfStep)

        if self.quarterStep:
            print "Quarter step results"
            passed &= self.testStepperResults(self.quarterStep)

        if self.sixteenthStep:
            print "Sixteeth step results"
            passed &= self.testStepperResults(self.sixteenthStep)

        if self.spiflashid:
            print "Spiflashid value (20)"
            print self.spiflashid
            passed &= self.testSpiflashid()

        if self.sdcard:
            print "SDCARD value (42)"
            print self.sdcard
            passed &= self.testSdcard()

        return passed

    def showErrors(self):
        print self.errors

    def restart(self):
        self.fullStep = []
        self.halfStep = []
        self.quarterStep = []
        self.sixteenthStep = []
        self.vrefs = []
        self.supplys = []
        self.supplyVoltages = []
        self.mosfetHigh = []
        self.mosfetLow = []
        self.endstopHigh = []
        self.endstopLow = []
        self.thermistors = []
        self.spiflashid = []
        self.sdcard = []
        self.errors = ""
        self.failedAxes = [False,False,False,False,False]
        self.failedMosfets = [False,False,False,False,False,False]
        self.failedEndstops = [False,False,False,False,False,False]

    def resultsDictionary(self):
        return dict(fullStep=self.fullStep,
                    halfStep=self.halfStep,
                    quarterStep=self.quarterStep,
                    sixteenthStep=self.sixteenthStep,
                    vrefs=self.vrefs,
                    supplys=self.supplys,
                    supplyVoltages=self.supplyVoltages,
                    mosfetHigh=self.mosfetHigh,
                    mosfetLow=self.mosfetLow,
                    endstopHigh=self.endstopHigh,
                    endstopLow=self.endstopLow,
                    thermistors=self.thermistors,
                    spiflashid=self.spiflashid,
                    sdcard=self.sdcard)

    def _wasTimedOut(self, vals):
        if -1 in vals:
            return True
        else:
            return False
            
    def _analogToVoltage(self, readings = [], voltage = 5, bits = 10, dividerFactor = 0.088):
        #divider factor is R2/(R1+R2)
        for val in readings:
            self.supplyVoltages += [(val/pow(2, bits))*(voltage/dividerFactor)]
