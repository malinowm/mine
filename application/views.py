from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.shortcuts import render_to_response
from django.template import RequestContext, loader
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from django import forms
from mineWebservice import *
from datetime import datetime
import thread
import os, tempfile, zipfile
from django.core.servers.basehttp import FileWrapper
from django.utils import simplejson
from pymongo import Connection
import re
from django.contrib.auth import authenticate, login
import logging
from math import sqrt, ceil
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

logger = logging.getLogger('admin')

HOST = '127.0.0.1'
PORT = 27017
connection = Connection(HOST, PORT)

class Counter:
    count = 0

    def increment(self):
        self.count += 1
        return ""
    def decrement(self):
        self.count -= 1
        return ""
    def reset(self):
        self.count = 0
        return ""
    def next(self):
        return (self.count + 1)

#data object to hold input data from user
class ContactForm(forms.Form):
    Email = forms.EmailField(max_length=256)
    Study = forms.CharField(max_length=16)

class LoginForm(forms.Form):
    Username = forms.CharField(max_length=16)
    Password = forms.CharField(max_length=16)

class RemovalForm(forms.Form):
    Studyno = forms.CharField(max_length=16)

class UploadForm(forms.Form):
    Name = forms.CharField(max_length=16)
    Email = forms.EmailField(max_length=256)
    File = forms.FileField()

class FileForm(forms.Form):
    File = forms.FileField()
    Study = forms.CharField(max_length=16)


@csrf_protect
def home(request):

    if request.user.is_authenticated():
        c = {}
        c.update(csrf(request))
        notice = ""

        if request.method == 'POST': # If the form has been submitted...
            downloadForm = ContactForm(request.POST) # A form bound to the POST data
            uploadForm = UploadForm(request.POST, request.FILES)
            if downloadForm.is_valid(): # All validation rules pass

                # Check for study existance, download files, upload files and notify user of progress via email
                try:
                    logger.info("user has requested that study " + downloadForm.cleaned_data['Study'] + " be processed")
                    thread.start_new_thread(downloadAndUpload, (downloadForm.cleaned_data['Study'].upper(), downloadForm.cleaned_data['Email']))
                    dt = str(datetime.now())
                    notice = dt[:len(dt)-7] + ": Thanks for using M.I.N.E. We will notify you via email at " + downloadForm.cleaned_data['Email'] + " as updates occur on study " + downloadForm.cleaned_data['Study'] + "."
                except:
                    notice = "an error has occur"
            elif uploadForm.is_valid():


                email = uploadForm.cleaned_data['Email']
                studyname = uploadForm.cleaned_data['Name'].replace(' ', '_')
                a = re.compile(r"\w+")
                possibleMatch = re.match(a,studyname)
                if possibleMatch:
                    if possibleMatch.group() == studyname:
                        if not alreadyRequested(studyname):

                        #create handler
                            filename = 'Studies/' + studyname +'/log.txt'
                            dir = os.path.dirname(filename)

                            if not os.path.exists(dir):
                                os.makedirs(dir)

                            hand = logging.FileHandler(filename)
                            hand.setLevel(logging.INFO)

                        #create formatter
                            formatter = logging.Formatter('%(asctime)s - %(message)s')

                        #set formatter for hand
                            hand.setFormatter(formatter)

                        #add hand to logger
                            logger.addHandler(hand)

                            handle_uploaded_file(request.FILES['File'], studyname)
                            logger.info("File " + studyname +".tab Successfully uploaded to temp file")
                            postRequest(studyname, email)
                            thread.start_new_thread(uploadAttrFile, (studyname, email))

                            notice = "Successfully began uploading your file, you will recieve and e-mail when it is done";
                        else:
                            notice = "That study name has already been used, Please try another."
                    else:
                        notice = "your file name is not formatted correctly. Please use alphanumeric characters spaces or underscores."
                else:
                    notice = "your file name is not formatted correctly. Please use alphanumeric characters spaces or underscores."
            else:
                notice = "Please Submit a valid form"

        #make form to store input
        downloadForm = ContactForm()
        uploadForm = UploadForm()
        #send http response back to user
        t = loader.get_template('home.html')
        c = RequestContext(request, {'downloadForm':downloadForm,'uploadForm':uploadForm,'notice': notice})
        return HttpResponse(t.render(c))
    else:
        logger.info('anonymous user has been redirected to login')
        return HttpResponseRedirect('login')




def get_samples(request, studyid):

    if alreadyRequested(studyid):
        temp = tempfile.NamedTemporaryFile()
        logger.info("user has downloaded the attribute data for study " + studyid)
        archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
        writeAttrFile(temp, studyid)
        archive.write(temp.name)
        archive.close()
        filename = temp.name # Select your files here.
        wrapper = FileWrapper(temp)
        response = HttpResponse(wrapper, content_type='application/zip')
        name = 'attachment; filename=' + studyid + '-attrData.zip'
        response['Content-Disposition'] = name
        response['Content-Length'] = temp.tell()
        temp.seek(0)
            
    else:
        logger.info("user has requested to download attribute data for study " + study + " but it does not exist in our database")
    return response

#upload handles user request to upload new study files
@csrf_protect
def upload_study(request):
    notice = "Please use alphanumeric characters spaces or underscores for study names."
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            
            email = form.cleaned_data['Email']
            studyname = form.cleaned_data['Name'].replace(' ', '_')
            a = re.compile(r"\w+")
            possibleMatch = re.match(a,studyname)
            if possibleMatch:
                if possibleMatch.group() == studyname:
                    if not alreadyRequested(studyname):
            
                        #create handler
                        filename = 'Studies/' + studyname +'/log.txt'
                        dir = os.path.dirname(filename)
                        
                        if not os.path.exists(dir):
                            os.makedirs(dir)
                        
                        hand = logging.FileHandler(filename)
                        hand.setLevel(logging.INFO)
                   
                        #create formatter     
                        formatter = logging.Formatter('%(asctime)s - %(message)s')
            
                        #set formatter for hand    
                        hand.setFormatter(formatter)
            
                        #add hand to logger
                        logger.addHandler(hand)

                        handle_uploaded_file(request.FILES['File'], studyname)
                        logger.info("File " + studyname +".tab Successfully uploaded to temp file")
                        postRequest(studyname, email)
                        thread.start_new_thread(uploadAttrFile, (studyname, email))

                        notice = "Successfully began uploading your file, you will recieve and e-mail when it is done";
                    else:
                        notice = "That study name has already been used, Please try another."
                else:
                    notice = "your file name is not formatted correctly. Please use alphanumeric characters spaces or underscores."
            else:
                notice = "your file name is not formatted correctly. Please use alphanumeric characters spaces or underscores."
    else:
        form = UploadForm()
    t = loader.get_template('upload.html')
    c = RequestContext(request, {'form':form, 'notice':notice})

    return HttpResponse(t.render(c))

#handle file uploads
def handle_uploaded_file(f, name):
    filename = "Studies/"+name+"/"+name+".tab"
    dir = os.path.dirname(filename)

    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(filename, 'w+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)

# login handles user requests to log in to the website
@csrf_protect
def login_auth(request):

    c = {}
    c.update(csrf(request))
    username = password = ''
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['Username']
            password = form.cleaned_data['Password']

            user = authenticate(username=username, password=password)
            try:
                if user.is_active:
                    logger.info("user " + username + " has logged in")
                    login(request, user)
                    return HttpResponseRedirect('/studies')
            except:
                logger.info("user " + username + " failed to log in")
                return HttpResponse("wrong")
    form = LoginForm()

    t = loader.get_template('login.html')
    c = RequestContext(request, {'form':form, 'username':username})
    return HttpResponse(t.render(c))

def tempview(request):

    t = loader.get_template('temp.html')
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

@csrf_protect
def admin(request):

    if request.user.is_authenticated():
        if request.method == 'POST':
            form = RemovalForm(request.POST)
            if form.is_valid():
            #remove study for database here
                logger.info("admin has removed " + form.cleaned_data['Studyno'])
                removeByNumber(form.cleaned_data['Studyno'])
                dropStudyData(form.cleaned_data['Studyno'])

    
        #get list of queued studies
        queuedlist = getQueuedStudyList()
        datelist = []

        #get list of dates studies requested
        for study in queuedlist:
            datelist.append(getDateRequested(study))

        #get last 100 lines of the admin.log file
        loglines = tail(open('Studies/admin.log'), 100)
        loglines.reverse()
        # return http response back to user

        form = RemovalForm()

        data = zip(queuedlist, datelist)
        t = loader.get_template('admin.html')
        c = RequestContext(request, {'form':form,'loglines':loglines,'data':data,'queuedlist':queuedlist, 'datelist':datelist,})
        return HttpResponse(t.render(c))
    else:
        logger.info('anonymous user has been redirected to login page')
        return HttpResponseRedirect('../login')



#data handles requests for the visualization page
#studynumber is required to be a valid GSE id of hte form GSE##### where # is a decimal digit
def data(request, studynumber):
    
    if request.user.is_authenticated():
        logger.info("user has viewed to see the visualization page")
        try:
            columns = getNumberOfColumns(str(studynumber))
            rows = getNumberOfRows(str(studynumber))
            date = getDateRequested(str(studynumber))
            
        #send http response back to user
            t = loader.get_template('index.html')
            c = RequestContext(request, {'studyid':studynumber,'columns':columns, 'rows':rows, 'date':date})
            return HttpResponse(t.render(c))
        except:
            t = loader.get_template('studyerror.html')
            c = RequestContext(request, {})
            return HttpResponse(t.render(c))

    else:
        logger.info('anonymous user has been redirected to login page')
        return HttpResponseRedirect('../../login')

#list handles requests for the requested studies page
def list(request):

    if request.user.is_authenticated():
        logger.info("user has requested to see the requested studies page")
        # get list of not queued not processed studies
        waitlist = getWaitingStudyList()
        # get list of queued studies
        queuedlist = getQueuedStudyList()
        # get list of processed studies
        processedlist = getProcessedStudyList()

        #send http response back to user
        t = loader.get_template('list.html')
        c = RequestContext(request, {'queuedlist':queuedlist,'processedlist':processedlist,'waitlist':waitlist,})
        return HttpResponse(t.render(c))

    else:
        logger.info('anonymous user has been redirected to login')
        return HttpResponseRedirect('../login')

#plist handles requests for the processed studies page
def plist(request):

    if request.user.is_authenticated():
        logger.info("user has requested to see the processed studies page")
        # get list of processed studies
        processedlist = getProcessedStudyList()
        
        # return http response back to user
        t = loader.get_template('plist.html')
        c = RequestContext(request, {'processedlist':processedlist,})
        return HttpResponse(t.render(c))

    else:
        logger.info("anonymous user has been redirected to login")
        return HttpResponseRedirect('../login')

#qlist handles requests for the queued studies page
def qlist(request):

    logger.info("user has requested to see the queued studies page")
        #get list of queued studies
    requestedlist = getStudyList()
    attributes = []
    queued = []
    for study in requestedlist:
        if hasAttributeData(study):
            attributes.append(True)
        else:
            attributes.append(False)
        if requestQueued(study):
            queued.append(True)
        else:
            queued.append(False)

    data = zip(requestedlist,attributes, queued)  
    
    paginator = Paginator(data, 50)
    
    page = request.GET.get('page')
    try:
        studylist = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        studylist = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        studylist = paginator.page(paginator.num_pages)

        # return http response back to user
    t = loader.get_template('qlist.html')
    c = RequestContext(request, {'studylist':studylist,})
    return HttpResponse(t.render(c))


#about handles requests for the about page
def about(request):

    if request.user.is_authenticated():
        # return http response back to user
        t = loader.get_template('about.html')
        c = RequestContext(request, {})
        return HttpResponse(t.render(c))

    else:
        return HttpResponseRedirect('../login')

def format(request):
        # return http response back to user
    t = loader.get_template('format.html')
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

    
#send_zipfile handles requests to download Study Data
#studynumber is required to be a string containing a valid GSE id of the form GSE##### where # is a decimal digit
def send_zipfile(request, studynumber):
    """                                                                         
    Create a ZIP file on disk and transmit it in chunks of 8KB,                 
    without loading the whole file into memory. A similar approach can          
    be used for large dynamic PDF files.                                        
    """

    logger.info("user has downloaded the study data for " + studynumber)
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
    
    path = 'Studies/' + studynumber + '/'
    listing = os.listdir(path)
    for file in listing:
        filename = file # Select your files here.                           
        archive.write(path + filename, filename) #studyid = 'filename'
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=' + studynumber + '.zip'
    response['Content-Disposition'] = name
    response['Content-Length'] = temp.tell()
    temp.seek(0)

    return response

#sendAllPairs handles requests to download All Pairs data
#studynumber is required to be a string containing a valid GSE id of the form GSE##### where # is a decimal digit
def sendAllPairs(request, studynumber):
    """
    Create a ZIP file on disk and transmit it in chunks of 8KB,
    without loading the whole file into memory. A similar approach can
    be used for large dynamic PDF files.
    """

    logger.info("user has downloaded the allpairs data for " + studynumber)
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

    path = 'Studies/' + studynumber + 'P/'
    listing = os.listdir(path)
    for file in listing:
        filename = file # Select your files here.
        archive.write(path + filename, filename) #studyid = 'filename'
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=' + studynumber + '-allpairs.zip'
    response['Content-Disposition'] = name
    response['Content-Length'] = temp.tell()
    temp.seek(0)

    return response

#sendLog handles requests to download Log files
#studynumber is required to be a string containing a valid GSE id of the form GSE##### where # is a decimal digit
def sendLog(request, studynumber):
    """
    Create a ZIP file on disk and transmit it in chunks of 8KB,
    without loading the whole file into memory. A similar approach can
    be used for large dynamic PDF files.
    """

    logger.info("user has downloaded the log for " + studynumber)

    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

    path = 'Studies/' + studynumber + '/'
    filename = 'log.txt' # Select your files here.
    archive.write(path + filename, filename) #studyid = 'filename'
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=' + studynumber + '-logfile.zip'
    response['Content-Disposition'] = name
    response['Content-Length'] = temp.tell()
    temp.seek(0)

    return response


#sendLog handles requests to download the admin.log file                                                      
def sendadminLog(request):
    """                                                                                              
    Create a ZIP file on disk and transmit it in chunks of 8KB,                                     
    without loading the whole file into memory. A similar approach can                         
    be used for large dynamic PDF files.                                                       
    """

    logger.info("admin has downloaded the admin log")

    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

    path = 'Studies/'
    filename = 'admin.log' # Select your files here.                                                   
    archive.write(path + filename, filename) #studyid = 'filename'                                   
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=adminlog.zip'
    response['Content-Disposition'] = name
    response['Content-Length'] = temp.tell()
    temp.seek(0)

    return response



#format data handles requests made on the visualization page for Study data and returns them to the applicaton in json format
def formatData(request):
        studyid = request.GET.get('studyid');
        var1 = request.GET.get('gene_x');
        var2 = request.GET.get('gene_y');
        
        try:
            x_data = RetrieveData(studyid,var1)
            y_data = RetrieveData(studyid,var2)
            data = []
        
            if x_data.count>0 and y_data.count>0:
                for i in xrange(len(x_data)):
                    result = {}
                    result["x"] = x_data[i]
                    result["y"] = y_data[i]
                    data.append(result)
        except:
            data = [{"this":"is_wrong"}]
        return HttpResponse(simplejson.dumps(data),mimetype="application/json")

def sendStudy(request, studyid):
    #packStudyData(studyid)
    return HttpResponse("This is not yet implemented")

def complete(request):
    studyid = request.GET.get('studyid');
    term = request.GET.get('term');
    
    ret = completeTerm(studyid, term);
    return HttpResponse(simplejson.dumps({"value": ret}), mimetype="application/json")

def geneExistance(request):
    studyid = request.GET.get('studyid');
    gene = request.GET.get('gene');

    ret = geneExists(studyid, gene)
    return HttpResponse(simplejson.dumps({"value": ret}), mimetype="application/json")

def getChartData(request):
    studyid = request.GET.get('studyid');

    try:
        ret = retrieveChartData(studyid)
        #ret = [{gene_x:gene_y, studyid:"this"}]
        return HttpResponse(ret ,mimetype="application/json")
    except:
        this = "this"
        is_wrong = "is_wrong"
        ret = {}
        return HttpResponse(simplejson.dumps(ret) ,mimetype="application/json")
    
def getAttrData(request):
    studyid = request.GET.get('studyid');
    
    try:
        ret = retrieveAttrData(studyid)
    except:
        ret = [{"this":"is_incorrect"}]
    return HttpResponse(simplejson.dumps(ret),mimetype="application/json")

def getSingleAttrData(request):
    studyid = request.GET.get('studyid');
    attr = request.GET.get('attr');

    try:
        ret = retrieveSingleAttr(studyid, attr)
    except:
        ret = [{"this":"is_incorrect"}]

    return HttpResponse(simplejson.dumps(ret),mimetype="application/json")

def singlePlot(request, studynumber):
    
    notice = ""
    gene_x = ""
    gene_y = ""
    try:
        gene_x = request.GET.get('gene_x');
        gene_y = request.GET.get('gene_y');
    except:
        notice = "Two genes must be requested to make a graph"

    t = loader.get_template('plot.html')
    c = RequestContext(request, {'notice':notice,'gene_x':gene_x,'gene_y':gene_y,'studyid': studynumber})
    return HttpResponse(t.render(c))

@csrf_protect
def plotList(request, studynumber):

    if request.method == 'POST':
        fileForm = FileForm(request.POST, request.FILES)
        if fileForm.is_valid():
            xList = []
            yList = []
            for chunk in request.FILES['File'].chunks():
                lines = chunk.split('\n')
                for line in lines:
                    genes = line.split(', ')
                    xList.append(genes[0])
                    yList.append(genes[1])
            pairs = zip(xList, yList)
            c = Counter()

            plotNumber = len(genePairs)
            tablelen = [1]*plotNumber
            
            columns = getNumberOfColumns(str(studynumber))
            rows = getNumberOfRows(str(studynumber))
            date = getDateRequested(str(studynumber))
            
            t = loader.get_template('thumbs.html')
            c = RequestContext(request, {'notice':notice,'pairs':pairs,'studyid': studynumber, 'plotNumber':plotNumber,'label':label,'tablelen':tablelen,'counter':c,'columns':columns,'rows':rows,'date':date,})
            return HttpResponse(t.render(c))
    else:
        notice = ""
        genes = ""
        label = ""

        try:
            genes = request.GET.get('genes')
            label = request.GET.get('label')
        except:
            notice = "The information entered was insufficient."
            
        genePairs = genes.split(':')
        plotNumber = len(genePairs)
        num = plotNumber/5
        tablelen = [1]*plotNumber
        xList = []
        yList = []

        columns = getNumberOfColumns(str(studynumber))
        rows = getNumberOfRows(str(studynumber))
        date = getDateRequested(str(studynumber))
        
        for pair in genePairs:
            ids = pair.split(',')
            xList.append(ids[0])
            yList.append(ids[1])

        pairs = zip(xList, yList)
        c = Counter()
        t = loader.get_template('thumbs.html')
        c = RequestContext(request, {'notice':notice,'pairs':pairs,'studyid': studynumber, 'plotNumber':plotNumber,'label':label,'tablelen':tablelen,'counter':c,'columns':columns,'rows':rows,'date':date,})
        return HttpResponse(t.render(c))

@csrf_protect
def thumbnails(request):

    if request.method == 'POST':
        fileForm = FileForm(request.POST, request.FILES)
        if fileForm.is_valid():
            xList = []
            yList = []
            for chunk in request.FILES['File'].chunks():
                lines = chunk.split('\n')
                for line in lines:
                    genes = line.split(', ')
                    xList.append(genes[0])
                    yList.append(genes[1].rstrip())
            pairs = zip(xList, yList)
            c = Counter()

            plotNumber = len(xList)
            tablelen = [1]*plotNumber

            studynumber = fileForm.cleaned_data['Study']
            columns = getNumberOfColumns(str(studynumber))
            rows = getNumberOfRows(str(studynumber))
            date = getDateRequested(str(studynumber))
            label = "geo_accession"

            t = loader.get_template('thumbs.html')
            con = RequestContext(request, {'pairs':pairs,'studyid': studynumber, 'plotNumber':plotNumber,'label':label,'tablelen':tablelen,'counter':c,'columns':columns,'rows':rows,'date':date,})
            return HttpResponse(t.render(con))
    else:

        studies = getQueuedStudyList()
        fileForm = FileForm()

        t = loader.get_template('thumbnails.html')
        c = RequestContext(request, {'studies':studies,"fileform":fileForm,})
        return HttpResponse(t.render(c))

def getAttributeKeys(request):
    studyid = request.GET.get('studyid');

    try:
        ret = retrieveAttrKeys(studyid)
    except:
        ret = ['none',]
    return HttpResponse(simplejson.dumps(ret),mimetype="application/json")

@csrf_protect
def downloadGraph(request):

#    graph = request.GET.get("graph");

    temp = tempfile.NamedTemporaryFile()
    # logger.info("user has downloaded the attribute data for study " + study)
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
    
    archive.write(temp.name)
    archive.close()
    filename = temp.name # Select your files here.
    #temp.write(graph);
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=graph.zip'
    response['Content-Disposition'] = name
    response['Content-Length'] = temp.tell()
    temp.seek(0)
    
    
    return response


def getGraph(request):
    fileContent = request.POST['svg']
    res = HttpResponse(fileContent)
    res['Content-Disposition'] = 'attachment; filename=graph.xml'
    return res


def uploadTest(request):
    t = loader.get_template('uploadtest.html')
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

def dashboard(request, studynumber):

    genes = getTwoGeneIds(studynumber, 0)
    minigenes = getTwoGeneIds(studynumber, 2)

    t = loader.get_template('dashboard.html')
    c = RequestContext(request, {'studyid':studynumber,'genex':genes[0],'geney':genes[1],'genex2':minigenes[0],'geney2':minigenes[1],})
    return HttpResponse(t.render(c))
