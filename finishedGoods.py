#!/usr/bin/env python

def main(date,dbConnection,dbTestStorage,testjig):
	dateTest = date
	testStorage = dbTestStorage
	cursor = dbConnection
	cursor.execute("""SELECT "serial", "timestamp"::date, testresults, COUNT("timestamp") FROM "public"."testdata"  WHERE "timestamp"::date=%s::date AND testresults='Passed' AND testjig='rambo' GROUP BY "serial","timestamp"::date,"testresults" ORDER BY "timestamp" """, (dateTest,))
	rows = cursor.fetchall()
	ramboNum = len(rows)
	cursor.execute("""SELECT "serial", "timestamp"::date, testresults, COUNT("timestamp") FROM "public"."testdata"  WHERE "timestamp"::date=%s::date AND testresults='Passed' AND testjig='minirambo' GROUP BY "serial","timestamp"::date,"testresults" ORDER BY "timestamp" """, (dateTest,))
	rows = cursor.fetchall()
	miniNum = len(rows)
	total = ramboNum + miniNum
	cursor.execute("""SELECT date FROM finishedgoodstracking WHERE date = %s""",(dateTest,))
	rows = cursor.fetchall()
	if len(rows) > 0:
		cursor.execute("""UPDATE finishedgoodstracking SET minirambos=%s, rambos=%s, total=%s WHERE date=%s""",(miniNum,ramboNum,total,dateTest))
	else:
		cursor.execute("""INSERT INTO finishedgoodstracking(date,minirambos,rambos,total) VALUES(%s::date,%s,%s,%s)""",(dateTest,miniNum,ramboNum,total))
	testStorage.commit()
        if testjig is "rambo":
	    print "Rambos for ",dateTest,": ",ramboNum
        if testjig is "minirambo":
	    print "miniRambos for ",dateTest,": ",miniNum
	#print "Finished Goods table updated"

