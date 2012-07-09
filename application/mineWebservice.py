#!/usr/local/bin/python

from pymongo import Connection
import os
import re
import logging
from datetime import datetime, date
import smtplib
import string
from ftplib import FTP
from geo_api.script import *
import time

#connection info
HOST = '127.0.0.1'
PORT = 27017

def writeAttrFile(f, studyid):
    #open file for writing
    #f = open(studyid +'.attr', 'w')

    #query database for all attributes

    #connection to the database                                                
    connection = Connection(HOST, PORT)
    db = connection.MINE

    attributes = db[studyid+'GSM'].find_one().keys()

    samples = db[studyid+'order'].find().distinct('GSM')
    #write attributes to file in form attribute_(attr) # # # #  where #'s are the sample's attributes and attr is the attribute name

    for attr in attributes:

        if not attr == '_id' and not attr == 'GSM':
            f.write('attribute_'+attr)
            for sample in samples:
                sample = sample.rstrip()
                samp = db[studyid+'GSM'].find({"geo_accession":sample}).distinct(attr)
                if samp[0]:
                    f.write('\t' + samp[0].encode('utf-8'))
                    for x in samp[1:]:
                        f.write(',' +x.encode('utf-8'))
            f.write('\n')

    Connection.disconnect(connection)
    #f.close()

def uploadAttrFile(studyid):

    #connection to the database
    connection = Connection(HOST, PORT)
    db = connection.MINE

    filepath = 'Studies/' + studyid +'/' + studyid + '.tab'
    f = open(filepath)
    logging.info(studyid + ".tab has been successfully open")
    attrlist = []
    ready = 0
    for line in f:
        #remove trailing newline character
        line = line.rstrip()
        if line[0] == '#':
            #line is header line
            gsm_ids = line.split("\t")
            gsm_ids = gsm_ids[1:]
            n = 1
            for id in gsm_ids:
                #check ids for semicolon separators
                more_ids = id.split(";")
                for x in more_ids:
                    #insert ids into database with no to keep order
                    db[studyid+"order"].insert({"no":n,"GSM":x})
                    n+=1
        else:
            #check for attribute line

            data = line.split("\t")

            result = re.match("attribute_", data[0])

            if result:
                #line is attribute line
                    no = 0
                    for cell in data[1:]:
                        #make list out of attributes separated by ,'s
                        if cell.find(',') > 0:
                            cell = cell.split(',')
                        #ready denotes weather or not all dicts have been initialized or not
                        if ready == 0:
                            attrlist.append({})
                            attrlist[no][(data[0][10:])] = cell
                        else:
                            attrlist[no][(data[0][10:])] = cell
                        no+=1
                    ready = 1
            else:
                #line is id/float data line
                db[studyid].insert({"id":data[0], "canonical_id":data[0].upper(), "data":data[1:]})

    no = 1
    #for each dict add id-GSM entry and insert
    logging.info("all lines successfully read")
    for entry in attrlist:
        #gsm_id = db[studyid +"order"].find({"no":no}).distinct("GSM")[0]
        #entry['GSM'] = gsm_id
        db[studyid+'GSM'].insert(entry)

    logging.info("data has been uploaded to database")
    markRequestQueued(studyid)
    Connection.disconnect(connection)
    #close and delete the file
    f.close()


# inserts a request document into the database if studyid has not yet been requested
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# email is required to be a valid email address
def postRequest(studyid, email, processed = False, queued = False):
        
        if not alreadyRequested(studyid):
		#connect
                connection = Connection(HOST, PORT)
                db = connection.MINE
		addresses = [email,]
		#insert data
                request = {"gse": studyid, "email": addresses, "datetime": datetime.now(), "processed": False, "queued":False}
                db.request.insert(request)
		#disconnect
                Connection.disconnect(connection)

# returns true if studyid has already been requested and returns false if studyid has not yet been requested
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def alreadyRequested(studyid):
	# connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	# reutrn if study has been requested and disconnect
        if db.request.find({"gse":studyid}).count() > 0:
                Connection.disconnect(connection)
                return True
        else:
                Connection.disconnect(connection)
                return False

# returns true if studyid has been processed and returns false if studyid is not yet processed
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def requestProcessed(studyid):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	# return if study is processed and disconnect
        if db.request.find({"gse":studyid, "processed":True}).count() > 0:
                Connection.disconnect(connection)
                return True
        else:
                Connection.disconnect(connection)
                return False

# returns true if the studyid has been queued and returns false if the studyid is not yet queued
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def requestQueued(studyid):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#return if study is queued and disconnect
        if db.request.find({"gse":studyid, "queued":True}).count() > 0:
                Connection.disconnect(connection)
                return True
        else:
                Connection.disconnect(connection)
                return False

# marks a request for studyid processed and sends an email stating the status to each person who has requested it.
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def markRequestProcessed(studyid):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#update request
        db.request.update({"gse":studyid,}, {"$set": {"processed":True,"queued":False}})
        #get emails of requestors
	email = db.request.find({"gse":studyid}).distinct("email")
        #disconnect
	Connection.disconnect(connection)
        #send processing finished e-mail
	sendEmail(email, studyid)

# marks a request for studyid queued.
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def markRequestQueued(studyid):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#update request
        db.request.update({"gse":studyid,}, {"$set": {"queued":True}})
        #disconnect
	Connection.disconnect(connection)
	logging.info("study " + studyid + "has been successfully queued")

# returns a list of distinct studyid's that have been requested as a list
def getStudyList():
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#get list of distinct GSEids
        x = db.request.find().distinct("gse")
	#disconnect
        Connection.disconnect(connection)
        return x

# returns a list of distinct studyid's that are queued for processing as a list
def getQueuedStudyList():
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#get list of distinct queued GSEids
	x = db.request.find({"queued":True}).distinct("gse")
	#disconnect
        Connection.disconnect(connection)
        return x

def getDateRequested(studyid):
	#connect
	connection = Connection(HOST, PORT)
	db = connection.MINE
	ret = db.request.find({"gse":studyid}).distinct("datetime")[0]
     	ret = ret.strftime("%B %d, %Y")
	Connection.disconnect(connection)
	return ret
	

# returns a list of distinct studyid's that have been processed as a list
def getProcessedStudyList():
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	# get list of distinct processed GSEids
	x =  db.request.find({"processed":True}).distinct("gse")
	#disconnect
        Connection.disconnect(connection)
        return x

# returns a list of distinct studyid's that have not been processed or queued as a list
def getWaitingStudyList():
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	# get list of distinct processed GSEids
	x =  db.request.find({"processed":False, "queued":False}).distinct("gse")
	#disconnect
        Connection.disconnect(connection)
        return x

# returns true if studyid has a folder on ftp server and returns false if a folder does not exist on ftp server or are unable to connect to the ftp server
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def isValidNumber(studyid):
    ftp = FTP('ftp.ncbi.nih.gov')
    try:
        #connect
        ftp.login()
    except:
        #exit on failure
        return False
    #change directory to folder containing GSE folders
    ftp.cwd('/pub/geo/DATA/SeriesMatrix/')
    try:
        #try changing directory into studyid folder
        ftp.cwd(studyid)
    except:
        #exit on failure
        ftp.quit()
        return False
    #exit on success
    ftp.quit()
    return True

# sends an e-mail to a list of addresses about the status of a studyid
# type is a variable that denotes which message to send and is an optional arguement, if omitted type will automatically be equal to 0
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# addresses is required to be a list of valid email addresses
def sendEmail(addresses, studyid, type = 0):

    # Type 0 message means the study has been successfully marked as processed and is ready for viewing.
    if type == 0:
        SUBJECT = 'Mine has processed your study!'
        MESSAGE = 'Your request for study ' + studyid + ' has been processed \n\n to view go to http://yates.webfactional.com/studies/'+studyid
    # Type 1 message means that the request for a study has been successfully submitted.
    elif type == 1:
        SUBJECT = 'Mine has recieved your study request!'
        MESSAGE = 'Your request for study ' + studyid + ' has been successfully recieved and will be queued for processing soon.'
    # type 2 message means that the request for a study was unsuccessfully submitted
    elif type == 2:
        SUBJECT = 'Mine was not able to find study'
        MESSAGE = 'Your request for study ' + studyid + ' was not successfully recieved. Please go to http://yates.webfactional.com/studies and try again.'
    # type 3 message means that a study has been successfully queued for processing.
    elif type == 3:
        SUBJECT = 'Mine has queued your study!'
        MESSAGE = 'Your request for study ' + studyid + ' was successfully queued and is awaiting processing. You may go to http://yates.webfactional.com/studies/list if you wish to access the queued data.'
    # type 4 message means that a study was unsuccessfully queued for processing and there was an error downloading or uploading.
    elif type == 4:
        SUBJECT = 'Mine was unable to queue your study'
        MESSAGE = 'Your request for study ' + studyid + ' was not successfully queued. There was an error downloading the file and uploading it to our database. Please try downloading again. If this error persists please contact us at ##INSERT EMAIL ADDRESS FOR CONTACTING HERE##'
    SENDER = 'noreply@yates.webfactional.com'

    for address in addresses:
	    #setup and send the e-mail
	    Body = string.join(( "From: %s" % SENDER,
				 "To: %s" % address,
				 "Subject: %s" % SUBJECT,
				 "",
				 MESSAGE
				 ), "\r\n")
    
	    server = smtplib.SMTP('smtp.webfaction.com')
	    server.login('minebox','b0d79559')
	    server.sendmail(SENDER, [address], Body)
	    server.quit()

# adds an e-mail address to the list of e-mail addresses stored with a request for a studyid
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# email is required to be a valid e-mail address
def addAddress(studyid, email):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#get email list and append new email
	emailList = db.request.find({"gse":studyid}).distinct("email")
	emailList.append(email);
	# update request document
	db.request.update({"gse":studyid}, {"$set": {"email":emailList}})
	#disconnect
	Connection.disconnect(connection)

# removes a request for studyid from database
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def removeByNumber(studyid):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#remove studyid request
        db.request.remove({"gse":studyid})
	#disconnect
        Connection.disconnect(connection)
	

def dropStudyData(studyid):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
        #remove study data
	db[studyid].drop()
	order = studyid+'order'
	db[order].drop()
	gsm = studyid+'GSM'
	db[gsm].drop()
        #disconnect
        Connection.disconnect(connection)

# uploads a pair of variable name and a list of data into database (A single line read for a study file) for studyid
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# varname is required to be a string
# floats is required to be a list of float values (float values can be formatted as strings or floats)
def uploadLine(studyid, varname, floats):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#create and upload line
        line = {"id": varname,"canonical_id":varname.upper(), "data": floats}
        db[studyid].insert(line)
	#disconnect
        Connection.disconnect(connection)

# returns a list of float values corresponding to id for studyid
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# id is required to be a string matching an id in studyid
def RetrieveData(studyid, id):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	# get list of data
	x = list( db[studyid].find({"canonical_id":id.upper()}) )
	#disconnect
        Connection.disconnect(connection)
	#return list of floats
	try:
		ret = map(float, x[0]['data'])
	except:
		ret = []
		for item in x[0]['data']:
			try:
				f = float(item)
			except:
				f = item = 0.00
			ret.append(f)
	return ret
def retrieveChartData(studyid, gene_x, gene_y):
	#connect                                                                                                                         
        connection = Connection(HOST, PORT)
        db = connection.MINE
        # get list of data                                                                                                               
	x = list( db[studyid].find({"canonical_id":gene_x.upper()}) )[0]['data']
	y = list( db[studyid].find({"canonical_id":gene_y.upper()}) )[0]['data']

        n = 1
	ret = []
	for t in x:
		entry = {}
		next = db[studyid +"order"].find({"no":n}).distinct("GSM")[0]
		data = db[studyid +"GSM"].find({"geo_accession":next}).distinct("characteristics_ch1")
		
		#change list of characteristics to dict
		sample = {}
		for item in data:
			pair = item.split(": ")
			sample[pair[0]] = getCorrectType(pair[1])
		sample['id'] = next
		entry["y"] = getCorrectType(y[n-1])
		entry["x"] = getCorrectType(x[n-1])
		entry["sample"] = sample
		ret.append(entry)
		n+=1

        #disconnect                                                                                                                      
        Connection.disconnect(connection)
                                                                                    
        return ret

# uploads all the files for a studyid into database line by line.
# studyid is required to be a string formatted GSE##### where # is a decimal digit
def uploadStudy(studyid):

        #path for study files
        path = 'Studies/' + studyid +'/'
        listing = os.listdir(path)

	connection = Connection(HOST, PORT)
	db = connection.MINE

        #for all studies (exclude the file log.txt)
        for file in listing:
                if not file == 'log.txt':
                        try:
                                #open the file
                                logging.info("trying to open " + file)
                                f = open(path + file)
                                count = 0

                                #for each line after the header
				logging.info("trying to read lines")
                                for line in f:
                                        count = count + 1
					
                                        if count > 1:
						logging.debug("reading line " + str(count))
                                                try:
                                                        #insert lines
							#logging.debug("splitting line")
                                                        cells = line.split("\t")
							#logging.debug("stripping newline char")
                                                        cells[-1] = cells[-1].rstrip()
							#logging.debug("uploading line")
                                                        #uploadLine(studyid, cells[0], cells[1:])
                                                        line = {"id": cells[0], "canonical_id":cells[0].upper(), "data": cells[1:]}
							db[studyid].insert(line)

                                                except:
                                                        logging.error("line " + count + " could not be read")
					else:
						logging.debug("header line read")
						gsm_ids = line.split("\t")
						gsm_ids = gsm_ids[1:]
						n = 1
						for id in gsm_ids:
							more_ids = id.split(";")
							for x in more_ids:
								db[studyid+"order"].insert({"no":n,"GSM":x})
								n+= 1
                                #close file
				logging.info("lines successfully read")
                                logging.info("closing " + file)
                                f.close()

				#mark request queued
				markRequestQueued(studyid)
				db[studyid].ensure_index("canonical_id",1)
                        except:
                                logging.error("Could not open " + file)
		
       	Connection.disconnect(connection)
                                
# uploads pairwise data for a studyid into the database 
# studyid is required to be a string formatted GSE#####P where # is a decimal digit
# var 1 is required to be a string matching an id in studyid
# var 2 is required to be a string matching an id in studyid
# mic is required to be a string containing a float value
# pcc is required to be a string containing a float value
def uploadProcessedData(studyid, var1, var2, mic, pcc):
	# connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#upload data
        data = {"var1": var1,"var2":var2, "mic": mic, "pcc": pcc}
        db[studyid].insert(data)
	#disconnect
        Connection.disconnect(connection)

# uploads a processed study to the database
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# path is required to be a string containing the systempath where varfile, micfile, and pccfile are stored
# varfile is required to be a string containing the name of the file containing the variable pairs
# micfile is required to be a string containing the name of the file containing the mic values
# pccfile is required to be a string containing the name of the file containing the pcc values 
def uploadProcessedStudy(studyid, path, varfile, micfile, pccfile):
	#logging
        logging.basicConfig(filename='DEBUG.log',level=logging.INFO)

	#check read permissions on all files
        logging.info("opening " + varfile)
        try:
                vars = open(path+varfile)
		vars.close()
        except:
                logging.error("could not open " + varfile)
        
        logging.info("opening " + micfile)
        try:        
                mic = open(path+micfile)
		mic.close()
        except:
                logging.error("could not open " + micfile)
                
        logging.info("opening " + pccfile)
        try:
                pcc = open(path+pccfile)
		pcc.close()
        except:
                logging.error("could not open " + pccfile)
                
        count = 0

	#open files
	vars = open(path + varfile)
	mic = open(path + micfile)
	pcc = open(path + pccfile)
        for line in vars:
                count += 1
		variables = []
		micvalue = ""
		pccvalue = ""

		#get next value from all files
                try:
                        variables = line.split(',')
			variables[1] = variables[1].rstrip()
                except:
                        logging.error("could not read line " + count + " from " + varfile)
                try:
                        micvalue = mic.readline()
			micvalue = micvalue.rstrip()
                except:
                        logging.error("could not read line " + count + " from " + micfile)
                try:
                        pccvalue = pcc.readline()
			pccvalue = pccvalue.rstrip()
                except:
                        logging.error("could not read line " + count + " from " + micfile)

		#upload document
                uploadProcessedData(studyid+"P", variables[0], variables[1], micvalue, pccvalue)

        logging.info("done uploading lines")

        logging.info("closing files")
	#close files
        vars.close()
        mic.close()
        pcc.close()
 
#return pcc value for two variables in studyid
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# var 1 is required to be a string matching an id in studyid
# var 2 is required to be a string matching an id in studyid
def getPccData(studyid, var1, var2):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	#get pcc data (should only come back in x or y)
        x = db[studyid+"P"].find({"var1":var1, "var2":var2}).distinct("pcc")
	y = db[studyid+"P"].find({"var2":var1, "var1":var2}).distinct("pcc")
	#return pcc data and disconnect
        if x.count > 0:
                Connection.disconnect(connection)
		return float(x)
	else:
                Connection.disconnect(connection)
		return float(y)

#return mic value for two variables
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# var 1 is required to be a string matching an id in studyid
# var 2 is required to be a string matching an id in studyid
def getMicData(studyid, var1, var2):
	#connect
        connection = Connection(HOST, PORT)
        db = connection.MINE
	# get mic data (should only come back in x or y)
        x = db[studyid+"P"].find({"var1":var1, "var2":var2}).distinct("mic")
        y = db[studyid+"P"].find({"var2":var1, "var1":var2}).distinct("mic")
	#return mic data and disconnect
        if x.count > 0:
                Connection.disconnect(connection)
                return float(x)
        else:
                Connection.disconnect(connection)
                return float(y)

# returns all vars paired with var in studyid
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# var is required to be a string matching an id in studyid
def getCorrespondingVars(studyid, var):
	#connect
	connection = Connection(HOST, PORT)
        db = connection.MINE
	# get all variable paired with var
	x = db[studyid+"P"].find({"var1":var}).distinct("var2") 
	y = db[studyid+"P"].find({"var2":var}).distinct("var1")
	#disconnect
	Connection.disconnect(connection)
	return x+y

# downloads studyid and uploads it to database, Sends emails to the person requesting when new update occurs.
# studyid is required to be a string formatted GSE##### where # is a decimal digit
# email is required to be a valid e-mail address
def downloadAndUpload(studyid, email):

	path = 'Studies/' + studyid + '/'
	logfile = path +'log.txt'
        #logging setup                                                                               
        #create logger                                                                         
        log = logging.getLogger()
        log.setLevel(logging.DEBUG)

        #create admin handler                                                                        

        loghand = logging.FileHandler(logfile)
        loghand.setLevel(logging.DEBUG)

        #create formatter                                                                            

        formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    

        loghand.setFormatter(formatter)

        #add adhand to logger                                                                        
        log.addHandler(loghand)

        
	if re.match("GSE", studyid) and isValidNumber(studyid):
                #if new request and valid GSE
                if not alreadyRequested(studyid):
                    
                    postRequest(studyid, email)
		    sendEmail([email], studyid, 1)
		    try:
			    main(studyid, None, "Studies/" + studyid)
       			    uploadStudy(studyid)
                            markRequestQueued(studyid)
			    sendEmail([email], studyid, 3)
		    except:
			    sendEmail([email], studyid, 4)
			    removeByNumber(studyid)
		    
		else:
			#add email request to email list in database
			addAddress(studyid, email)
	else:
		 #email out to list that invalid studyid
		 sendEmail([email], studyid, 2)

	loghand.flush()
	loghand.close()
	log.handlers = []

def packStudyData(studyid):
	#connect                                                                                      
        connection = Connection(HOST, PORT)
        db = connection.MINE

	#get data from database
	vars = db['GSE' + studyid].find()
	
	#open file
	f=open('GSE' + studyid +'-data.txt','w')
	
	#for each gene id
	for x in vars:
		#write the id name
		f.write("%s\t" % x['id'])
		#for each float in data associated with gene id
		for token in x['data']:
			#write floats separated by tabs
			f.write("%s\t" % token)
		f.write("\n")
			
	f.close()
	
	Connection.disconnect(connection)


def completeTerm(studyid, term):

	connection = Connection(HOST, PORT)
        db = connection.MINE

        #get data from database

	search = "^" + str(term)
	ret = []
	ret = db[studyid].find({"canonical_id": { '$regex' : search, '$options': 'i'}}).distinct("canonical_id")[:10]

	Connection.disconnect(connection)
	return ret

def geneExists(studyid, gene):

	connection = Connection(HOST, PORT)
        db = connection.MINE

        #get data from database                                                 
	ret = False
        if db[studyid].find({"canonical_id":gene.upper()}).count() > 0:
		ret = True

	Connection.disconnect(connection)
        return ret

def getNumberOfColumns(studyid):
	connection = Connection(HOST, PORT)
        db = connection.MINE

        #get data from database                                                                                                                                                                          
	x = len(db[studyid].find_one()['data'])
        Connection.disconnect(connection)
        return x

def getNumberOfRows(studyid):
	connection = Connection(HOST, PORT)
	db = connection.MINE

        #get data from database                                                                                                                                                                             
	
	ret = db[studyid].find().count()
        Connection.disconnect(connection)
        return ret


#reads last n lines of a file
#f is a file object
#n is required to be an integer greater than 0
def tail(f, n):
    assert n >= 0
    pos, lines = n+1, []
    while len(lines) <= n:
        try:
                f.seek(-pos, 2)
        except IOError:
                f.seek(0)
                break
        finally:
                lines = list(f)
        pos *= 2
    return lines[-n:]

def getCorrectType(x):
	if x.isdigit():
		ret = int(x)
	else:
		try:
			ret = float(x)
		except ValueError:
			ret = x
	return ret
