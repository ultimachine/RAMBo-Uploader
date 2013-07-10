from termcolor import colored

class TestProcessor():
    def __init__(self):
        self.fullStep = []
        self.halfStep = []
        self.quarterStep = []
        self.sixteenthStep = []
        self.vrefs = []
        self.supplys = []
        self.mosfetHigh = []
        self.mosfetLow = []
        self.thermistors = []
        self.errors = ""
        self.axisNames = ["X","Y","Z","E0","E1"]
        self.thermistorNames = ["T0","T1","T2"]
        self.supplyNames = ["Extruder Rail","Bed Rail"]
        self.failedAxes = [False,False,False,False,False]

    def testVrefs(self):
        passed = True
        if self._wasTimedOut(self.vrefs):
            print colored("...Timed out at vref test", 'red')
            return False
        for idx, val in enumerate(self.vrefs):
            if not 170 <= val <= 195:
                self.errors += colored(self.axisNames[idx] + " axis vref incorrect\n", 'red')
                passed &= False
        if max(self.vrefs) - min(self.vrefs) >= 15:
            self.errors +=  colored("Vref variance too high!\n",'red')
            passed &= False
        return passed

    def testSupplys(self):
        passed = True
        if self._wasTimedOut(self.supplys):
            print colored("...Timed out at supply test", 'red')
            return False
        for idx, val in enumerate(self.supplys):
            if not 210 <= val <= 220:
                self.errors += colored("Test " + self.supplyNames[idx] + " supply\n", 'red')
                passed &= False
        return passed

    def testThermistors(self):
        passed = True
        if self._wasTimedOut(self.thermistors):
            print colored("...Timed out at thermistor test", 'red')
            return False
        for idx, val in enumerate(self.thermistors):
            if not 975 <= val <= 985:
                self.errors += colored("Check Thermistor" + self.thermistorNames[idx] + "\n", 'red')
                passed = False
        return passed

    def testMosfetLow(self):
        passed = True
        if self._wasTimedOut(self.mosfetLow):
            print colored("...Timed out at MOSFET low test", 'red')
            return False
        for idx, val in enumerate(self.mosfetLow):
            if not val == 1:
                self.errors += colored("Check MOSFET " + str(idx) + "\n", 'red')
                passed = False
        return passed

    def testMosfetHigh(self):
        passed = True
        if self._wasTimedOut(self.mosfetHigh):
            print colored("...Timed out at MOSFET high test", 'red')
            return False
        for idx, val in enumerate(self.mosfetHigh):
            if not val == 0:
                self.errors += colored("Check MOSFET " + str(idx) + "\n", 'red')
                passed = False
        return passed

    def testStepperResults(self, vals):
        passed = True
        if self._wasTimedOut(vals):
            print colored("...Timed out at stepper test", 'red')
            return False
        for i in range(5):
            forward = vals[i]
            reverse = vals[i+5]
            print "Forward -> " + str(forward) + "Reverse -> " + str(reverse)
            for j in range(5):
	       validRange = range(reverse[4-j]-10,reverse[4-j]+10)
               if not forward[j] in validRange and not self.failedAxes[i]: 
                    self.errors += colored("Check "+self.axisNames[i]+" stepper\n", 'red')
                    self.failedAxes[i] = True
                    passed = False
        return passed 
        
    def verifyAllTests(self):
        passed = True
        
        if self.supplys: #Just realized this is spelled wrong
            print "Supply voltage values..."
            print self.supplys    
            passed &= self.testSupplys()    

        if self.vrefs:
            print "Vref values..."
            print self.vrefs
            passed &= self.testVrefs()

        if self.thermistors:
            print "Target thermistor readings..."
            print self.thermistors
            passed &= self.testThermistors()

        if self.mosfetHigh:
            print "Mosfet high values..."
            print self.mosfetHigh
            passed &= self.testMosfetHigh()

        if self.mosfetLow:
            print "Mosfet low values..."
            print self.mosfetLow
            passed &= self.testMosfetLow()

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
        self.mosfetHigh = []
        self.mosfetLow = []
        self.thermistors = []
        self.errors = ""
        self.failedAxes = [False,False,False,False,False]

    def _wasTimedOut(self, vals):
        if -1 in vals:
            return True
        else:
            return False
