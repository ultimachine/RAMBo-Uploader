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

    def upload(self, target, timeout = 15):
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
        if self.autoEraseFlash is False:
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


        #call avrdude as a subprocess
        self.uploadProcess = subprocess.Popen(cmd)
        timeoutCount = 0
        while self.uploadProcess.poll() is None: # still alive
            time.sleep(0.5)
            timeoutCount += 0.5
            if timeoutCount == timeout:
                self.uploadProcess.kill()
                return False
        return True
