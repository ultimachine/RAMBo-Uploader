import psycopg2

class PostgresDatabase():
    def __init__(self, info):
        self.info = info
        self.storage = None

    def open(self):
        if not self.isOpen():
            self.storage = psycopg2.connect(Self.info)
            if self.storage is None:
                raise Exception("Could not open database")

    def isOpen(self):
        return self.storage is not None

    def close(self):
        if self.storage:
            self.storage.close()
            self.storage = None

    def post(self, serial, results, version, details):
        was_open = self.isOpen()
        self.open()
        cursor = self.storage.cursor()
        cursor.execute("""INSERT INTO testdata(serial, timestamp, testresults, testversion, testdetails) VALUES (%s, %s, %s, %s, %s)""", (serial, 'now', results, version, details))
        self.storage.commit()
        if not was_open:
            self.close()
