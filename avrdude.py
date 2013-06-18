import subprocess

#
# AVRDUDE, dude
#
class avrdude():
	"avrdude properties"
	def __init__(self):
		self.path = ""
		self.programmer = ""
		self.programmerSN = ""
		self.port = ""
	def upload(self, target):
		#call avrdude as a subprocess
		cmd = self.path + " -c " + self.programmer + " -P " + self.port + ":" +self.programmerSN
		if target.name:
			cmd += " -p " + target.name
		if target.bootloader:
			cmd += " -U " + target.bootloader
		if target.extFuse:
			cmd += " -Uefuse:w:" + target.extFuse + ":m"
		if target.highFuse:
			cmd += " -Uhfuse:w:" + target.highFuse + ":m"
		if target.lowFuse:
			cmd += " -Ulfuse:w:" + target.lowFuse + ":m"
		if target.lockBits:
			cmd += " -Ulock:w:" +target.lockBits + ":m"
		print(cmd)
		args = shlex.split(cmd)
		self.uploadProcess = subprocess.Popen(args, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
		

