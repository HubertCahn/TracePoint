import MySQLdb

class MyDataBase:
    db = None

    def __init__(self):
        self.connect()
        return

    def connect(self):
        self.db = MySQLdb.connect(
            host = "localhost",
            port = 3306,
            user = "root",
            passwd = "iems5722",
            db = "Trace",
            use_unicode = True,
            charset = "utf8",
        )
        self.cursor = self.db.cursor(MySQLdb.cursors.DictCursor)
        return
