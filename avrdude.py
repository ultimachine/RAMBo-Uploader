import subprocess
import time

#
# AVRDUDE, dude
#
class Avrdude():
    "avrdude properties"
    def __init__(self):
        self.path = ""
        self.programmer = ""
        self.programmerSN = ""
        self.port = ""
        self.baudrate = ""
        self.configFile = ""
        self.autoEraseFlash = True

    def upload(self, target, timeout = 25):
        #assemble argument array
        cmd = [self.path, "-c", self.programmer, "-P", self.port]
        if self.programmerSN:
            cmd[2].append(":" + self.programmerSN)
        if target.name:
            cmd.append("-p" + target.name)
        if self.baudrate:
            cmd.append("-b" + self.baudrate)
        if self.configFile:
            cmd.append("-C" + self.configFile)
        if self.autoEraseFlash:
            cmd.append("-D")
        if target.bootloader:
            cmd.append("-Uflash:w:" + target.bootloader + ":i")
        if target.extFuse:
            cmd.append("-Uefuse:w:" + target.extFuse + ":m")
        if target.highFuse:
            cmd.append("-Uhfuse:w:" + target.highFuse + ":m")
        if target.lowFuse:
            cmd.append("-Ulfuse:w:" + target.lowFuse + ":m")
        if target.lockBits:
            cmd.append("-Ulock:w:" +target.lockBits + ":m")

        print(cmd)
        #call avrdude as a subprocess
        self.uploadProcess = subprocess.Popen(cmd)
        time.sleep(timeout)
        if not self.uploadProcess.poll(): # still alive
            self.uploadProcess.kill()
            return False
        else:
            return True
