import datetime

class LogDatabase():
    def __init__(self, path):
        self.path = path
        self.fd = None

    def open(self):
        if self.fd is None:
            self.fd = open(self.path, 'a')

    def isOpen(self):
        return self.fd is not None

    def close(self):
        if self.fd:
            self.fd.close()
            self.fd = None

    def post(self, serial, results, version, details):
        was_open = self.isOpen()
        self.open()
        self.fd.write("*******************  %s  ********************\n" %datetime.datetime.now())
        self.fd.write("Serial number : %s\n" % (serial))
        self.fd.write("Version : %s\n" % (version))
        self.fd.write("%s\n%s\n\n" % (results, details))
        self.fd.flush()
        if not was_open:
            self.close()
