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
        
    def testVrefs(self):
        passed = True
        for idx, val in enumerate(self.vrefs):
            if not 170 <= val <= 195:
                self.errors += colored(self.axisNames[idx] + " axis vref incorrect\n", 'red')
                passsed &= False
        if max(self.vrefs) - min(self.vrefs) >= 15:
            self.errors +=  colored("Vref variance too high!\n",'red')
            passed &= False
        return passed

    def testSupplys(self):
        passed = True
        for idx, val in enumerate(self.supplys):
            if not 210 <= val <= 220:
                self.errors += colored("Test " + self.supplyNames[idx] + " supply\n", 'red')
                passed &= False
        return passed

    def testThermistors(self):
        passed = True
        for idx, val in enumerate(self.thermistors):
            if not 975 <= val <= 985:
                self.errors += colored("Check Thermistor" + self.thermistorNames[idx] + "\n", 'red')
                passed = False
        return passed

    def testMosfetLow(self):
        passed = True
        for idx, val in enumerate(self.mosfetLow):
            if not val == 1:
                self.errors += colored("Check MOSFET " + str(idx) + "\n", 'red')
                passed = False
        return passed

    def testMosfetHigh(self):
        passed = True
        for idx, val in enumerate(self.mosfetHigh):
            if not val == 0:
                self.errors += colored("Check MOSFET " + str(idx) + "\n", 'red')
                passed = False
        return passed

    def testStepperResults(self, vals):
        passed = True
        for i in range(5):
            forward = vals[i]
            reverse = vals[i+5]
            print "Forward -> " + str(forward) + "Reverse -> " + str(reverse)
            for j in range(5):
                if forward[j] in range(reverse[4-j]-10,reverse[4-j]+10):
                    pass
                else: 
                    self.errors += colored("Check "+self.axisNames[i]+" stepper\n", 'red')
                    passed = False
        return passed 
        
    def verifyAllTests(self):
        passed = True
        
        print "Supply voltage values..."
        print self.supplys    
        passed &= self.testSupplys()    

        print "Vref values..."
        print self.vrefs
        passed &= self.testVrefs()

        print "Target thermistor readings..."
        print self.thermistors
        passed &= self.testThermistors()

        print "Mosfet high values..."
        print self.mosfetHigh
        passed &= self.testMosfetHigh()

        print "Mosfet low values..."
        print self.mosfetLow
        passed &= self.testMosfetLow()

        print "Full step results"
        passed &= self.testStepperResults(self.fullStep)

        print "Half step results"
        passed &= self.testStepperResults(self.halfStep)

        print "Quarter step results"
        passed &= self.testStepperResults(self.quarterStep)

        print "Sixteeth step results"
        passed &= self.testStepperResults(self.sixteenthStep)
        
        if not passed:
            self.errors = colored("Board failed\n", 'red') + self.errors
        else:
            self.errors = colored("Board passed\n", 'green') + self.errors
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

