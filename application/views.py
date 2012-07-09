from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.shortcuts import render_to_response
from django.template import RequestContext, loader
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from django import forms
#from geo_api.script import *
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


HOST = '127.0.0.1'
PORT = 27017
connection = Connection(HOST, PORT)

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

@csrf_protect
def get_samples(request):
    c = {}
    notice = ""
    c.update(csrf(request))
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():

            study = form.cleaned_data['Study']
            email = form.cleaned_data['Email']

            if alreadyRequested(study):
                temp = tempfile.NamedTemporaryFile()

                archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
                writeAttrFile(temp, study)
                archive.write(temp.name)
                archive.close()
                filename = temp.name # Select your files here.
                wrapper = FileWrapper(temp)
                response = HttpResponse(wrapper, content_type='application/zip')
                name = 'attachment; filename=' + study + '-attrData.zip'
                response['Content-Disposition'] = name
                response['Content-Length'] = temp.tell()
                temp.seek(0)
            

                return response
            else:
                notice = "The Study that you have requested to download attribute data for does not exist in our database"
        else:
            notice = "The information that You have entered is incorrect"
    form = ContactForm()

    t = loader.get_template('samples.html')
    c = RequestContext(request, {'form':form, 'notice':notice})
    return HttpResponse(t.render(c))

#upload handles user request to upload new study files
@csrf_protect
def upload_study(request):
    notice = "Please use alphanumeric characters spaces or underscores for study names."
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            
            studyname = form.cleaned_data['Name'].replace(' ', '_')
            a = re.compile(r"\w+ \w+ \w+ \w+")
            if re.match(a,studyname):
            #create logger
                uplogger = logging.getLogger()
                uplogger.setLevel(logging.INFO)
                
        #create admin handler
                filename = 'Studies/' + studyname +'/log.txt'
                dir = os.path.dirname(filename)
                
                if not os.path.exists(dir):
                    os.makedirs(dir)
                    
                hand = logging.FileHandler(filename)
                hand.setLevel(logging.INFO)
                    
        #create formatter
                    
                formatter = logging.Formatter('%(asctime)s - %(message)s')
            
        #set formatter for adhand
            
                hand.setFormatter(formatter)
            
        #add adhand to logger
                uplogger.addHandler(hand)


                handle_uploaded_file(request.FILES['File'], studyname)
                logging.info("File " + studyname +".tab Successfully upload") 
                postRequest(studyname, form.cleaned_data['Email'])
                thread.start_new_thread(uploadAttrFile, (studyname,))
                
                hand.flush()
                hand.close()
                uplogger.handlers = []
                notice = "Successfully uploaded your file";
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

    #create logger                                                                                
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                         
    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                             
    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                     
    adhand.setFormatter(formatter)

        #add adhand to logger                                                                         
    logger.addHandler(adhand)


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

    adhand.flush()
    adhand.close()
    logger.handlers = []
    t = loader.get_template('login.html')
    c = RequestContext(request, {'form':form, 'username':username})
    return HttpResponse(t.render(c))

def tempview(request):

    t = loader.get_template('temp.html')
    c = RequestContext(request, {})
    return HttpResponse(t.render(c))

@csrf_protect
def admin(request):

    #create logger                                                                                    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                       
                                                                                                    
    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                           
                                                                                                     
    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                   
    
    adhand.setFormatter(formatter)

        #add adhand to logger                                                                       
    logger.addHandler(adhand)                         

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

        # return http response back to user

        form = RemovalForm()

        adhand.flush()
        adhand.close()
        logger.handlers = []
        data = zip(queuedlist, datelist)
        t = loader.get_template('admin.html')
        c = RequestContext(request, {'form':form,'loglines':loglines,'data':data,'queuedlist':queuedlist, 'datelist':datelist,})
        return HttpResponse(t.render(c))
    else:
        logger.info('anonymous user has been redirected to login page')
        adhand.flush()
        adhand.close()
        logger.handlers=[]
        return HttpResponseRedirect('../login')

    

# home handles requests for the home page
@csrf_protect
def home(request):

    #create logger                                                                                  
                                                                                                     
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                       

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                           

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                   

    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

    if request.user.is_authenticated():
        c = {}
        c.update(csrf(request))
        notice = ""
    
        if request.method == 'POST': # If the form has been submitted...
            form = ContactForm(request.POST) # A form bound to the POST data
            if form.is_valid(): # All validation rules pass
            
                # Check for study existance, download files, upload files and notify user of progress via email
                try:
                    logger.info("user has requested that study " + form.cleaned_data['Study'] + " be processed")
                    thread.start_new_thread(downloadAndUpload, (form.cleaned_data['Study'].upper(), form.cleaned_data['Email']))
                    dt = str(datetime.now())
                    notice = dt[:len(dt)-7] + ": Thanks for using M.I.N.E. We will notify you via email at " + form.cleaned_data['Email'] + " as updates occur on study " + form.cleaned_data['Study'] + "."
                except:
                    notice = "an error has occur"
        #make form to store input
        form = ContactForm()

        adhand.flush()
        adhand.close()
        logger.handlers = []
        #send http response back to user
        t = loader.get_template('home.html')
        c = RequestContext(request, {'form':form,'notice': notice})
        return HttpResponse(t.render(c))
    else:
        logger.info('anonymous user has been redirected to login')
        adhand.flush()
        adhand.close()
        return HttpResponseRedirect('login')


#data handles requests for the visualization page
#studynumber is required to be a valid GSE id of hte form GSE##### where # is a decimal digit
def data(request, studynumber):

    #create logger                                                                                   
                                                                                                    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        
    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            
    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    
    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)
    
    if request.user.is_authenticated():
        logger.info("user has viewed to see the visualization page")
        logger.handlers = []
        adhand.flush()
        adhand.close()
        try:
            columns = getNumberOfColumns(str(studynumber))
            rows = getNumberOfRows(str(studynumber))
            date = getDateRequested(str(studynumber))
            
        #send http response back to user
            t = loader.get_template('index.html')
            c = RequestContext(request, {'studyid':studynumber,'columns':columns, 'rows':rows, 'date':date})
            return HttpResponse(t.render(c))
        except:
            return HttpResponse("this Study has not yet been processed and is not available for review")

    else:
        logger.info('anonymous user has been redirected to login page')
        logger.handlers = []
        adhand.flush()
        adhand.close()
        return HttpResponseRedirect('../../login')

#list handles requests for the requested studies page
def list(request):

    #create logger                                                                                  

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    

    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

    if request.user.is_authenticated():
        logger.info("user has requested to see the requested studies page")
        # get list of not queued not processed studies
        waitlist = getWaitingStudyList()
        # get list of queued studies
        queuedlist = getQueuedStudyList()
        # get list of processed studies
        processedlist = getProcessedStudyList()

        adhand.flush()
        adhand.close()
        logger.handlers = []
        #send http response back to user
        t = loader.get_template('list.html')
        c = RequestContext(request, {'queuedlist':queuedlist,'processedlist':processedlist,'waitlist':waitlist,})
        return HttpResponse(t.render(c))

    else:
        logger.info('anonymous user has been redirected to login')
        adhand.flush()
        adhand.close()
        logger.handlers = []
        return HttpResponseRedirect('../login')

#plist handles requests for the processed studies page
def plist(request):

    #create logger                                                                                   
                                                                                                    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    

    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

    if request.user.is_authenticated():
        logger.info("user has requested to see the processed studies page")
        # get list of processed studies
        processedlist = getProcessedStudyList()
        
        adhand.flush()
        adhand.close()
        logger.handlers = []
        # return http response back to user
        t = loader.get_template('plist.html')
        c = RequestContext(request, {'processedlist':processedlist,})
        return HttpResponse(t.render(c))

    else:
        logger.info("anonymous user has been redirected to login")
        adhand.flush()
        adhand.close()
        logger.handlers = []
        return HttpResponseRedirect('../login')

#qlist handles requests for the queued studies page
def qlist(request):

    #create logger                                                                                   
                                                                                                     
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    

    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

    if request.user.is_authenticated():
        logger.info("user has requested to see the queued studies page")
        #get list of queued studies
        queuedlist = getQueuedStudyList()
        
        adhand.flush()
        adhand.close()
        logger.handlers = []
        # return http response back to user
        t = loader.get_template('qlist.html')
        c = RequestContext(request, {'queuedlist':queuedlist,})
        return HttpResponse(t.render(c))

    else:
        logger.info('anonymous user has been redirected to login')
        adhand.flush()
        adhand.close()
        logger.handlers = []
        return HttpResponseRedirect('../login')

#about handles requests for the about page
def about(request):

    if request.user.is_authenticated():
        # return htp response back to user
        t = loader.get_template('about.html')
        c = RequestContext(request, {})
        return HttpResponse(t.render(c))

    else:
        return HttpResponseRedirect('../login')

#send_zipfile handles requests to download Study Data
#studynumber is required to be a string containing a valid GSE id of the form GSE##### where # is a decimal digit
def send_zipfile(request, studynumber):
    """                                                                         
    Create a ZIP file on disk and transmit it in chunks of 8KB,                 
    without loading the whole file into memory. A similar approach can          
    be used for large dynamic PDF files.                                        
    """

    #create logger                                                                                   
                                                                                                     
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    
    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

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
    
    adhand.flush()
    adhand.close()
    logger.handlers = []
    return response

#sendAllPairs handles requests to download All Pairs data
#studynumber is required to be a string containing a valid GSE id of the form GSE##### where # is a decimal digit
def sendAllPairs(request, studynumber):
    """
    Create a ZIP file on disk and transmit it in chunks of 8KB,
    without loading the whole file into memory. A similar approach can
    be used for large dynamic PDF files.
    """

    #create logger                                                                                   
                                                                                                     
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    

    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

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

    adhand.flush()
    adhand.close()
    logger.handlers = []
    return response

#sendLog handles requests to download Log files
#studynumber is required to be a string containing a valid GSE id of the form GSE##### where # is a decimal digit
def sendLog(request, studynumber):
    """
    Create a ZIP file on disk and transmit it in chunks of 8KB,
    without loading the whole file into memory. A similar approach can
    be used for large dynamic PDF files.
    """

    #create logger                                                                                   
                                                                                                     
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    

    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

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

    adhand.flush()
    adhand.close()
    logger.handlers = []
    return response


#sendLog handles requests to download the admin.log file                                                      
def sendadminLog(request):
    """                                                                                              
    Create a ZIP file on disk and transmit it in chunks of 8KB,                                     
    without loading the whole file into memory. A similar approach can                         
    be used for large dynamic PDF files.                                                       
    """

    #create logger                                                                                   

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

        #create admin handler                                                                        

    adhand = logging.FileHandler('Studies/admin.log')
    adhand.setLevel(logging.INFO)

        #create formatter                                                                            

    formatter = logging.Formatter('%(asctime)s - %(message)s')

        #set formatter for adhand                                                                    

    adhand.setFormatter(formatter)

        #add adhand to logger                                                                        
    logger.addHandler(adhand)

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

    adhand.flush()
    adhand.close()
    logger.handlers = []
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
        return HttpResponse(simplejson.dumps({"data": data}),mimetype="application/json")

def sendStudy(request, studyid):
    packStudyData(studyid)
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
    gene_x = request.GET.get('gene_x');
    gene_y = request.GET.get('gene_y');

    try:
        ret = retrieveChartData(studyid, gene_x, gene_y)
        #ret = [{gene_x:gene_y, studyid:"this"}]
    except:
        ret = [{"this":"is_wrong"}]
    return HttpResponse(simplejson.dumps(ret),mimetype="application/json")
