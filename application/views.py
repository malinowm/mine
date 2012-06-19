from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.shortcuts import render_to_response
from django.template import RequestContext, loader
from django.core.context_processors import csrf
from django.views.decorators.csrf import csrf_protect
from django import forms
#from geo_api.script import *
from mineWebservice import postRequest, alreadyRequested, getQueuedStudyList, getProcessedStudyList, RetrieveData, isValidNumber, downloadAndUpload, getWaitingStudyList, getDateRequested, removeByNumber, dropStudyData
from datetime import datetime
import thread
import os, tempfile, zipfile
from django.core.servers.basehttp import FileWrapper
from django.utils import simplejson
from pymongo import Connection
import re
from django.contrib.auth import authenticate, login

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
                    login(request, user)
                    return HttpResponseRedirect('/studies')
            except:
                return HttpResponse("wrong")
    form = LoginForm()

    t = loader.get_template('login.html')
    c = RequestContext(request, {'form':form, 'username':username})
    return HttpResponse(t.render(c))

@csrf_protect
def admin(request):

    if request.user.is_authenticated():
        if request.method == 'POST':
            form = RemovalForm(request.POST)
            if form.is_valid():
            #remove study for database here
                removeByNumber(form.cleaned_data['Studyno'])
                dropStudyData(form.cleaned_data['Studyno'])

                

    
        #get list of queued studies
        queuedlist = getQueuedStudyList()
        datelist = []

        #get list of dates studies requested
        for study in queuedlist:
            datelist.append(getDateRequested(study))

        # return http response back to user

        form = RemovalForm()

        data = zip(queuedlist, datelist)
        t = loader.get_template('admin.html')
        c = RequestContext(request, {'form':form,'data':data,'queuedlist':queuedlist, 'datelist':datelist,})
        return HttpResponse(t.render(c))
    else:
        return HttpResponseRedirect('../login')

    

# home handles requests for the home page
@csrf_protect
def home(request):
    if request.user.is_authenticated():
        c = {}
        c.update(csrf(request))
        notice = ""
    
        if request.method == 'POST': # If the form has been submitted...
            form = ContactForm(request.POST) # A form bound to the POST data
            if form.is_valid(): # All validation rules pass
            
                # Check for study existance, download files, upload files and notify user of progress via email
                try:
                    thread.start_new_thread(downloadAndUpload, (form.cleaned_data['Study'].upper(), form.cleaned_data['Email']))
                    dt = str(datetime.now())
                    notice = dt[:len(dt)-7] + ": Thanks for using M.I.N.E. We will notify you via email at " + form.cleaned_data['Email'] + " as updates occur on study " + form.cleaned_data['Study'] + "."
                except:
                    notice = "an error has occur"
        #make form to store input
        form = ContactForm()

        #send http response back to user
        t = loader.get_template('home.html')
        c = RequestContext(request, {'form':form,'notice': notice})
        return HttpResponse(t.render(c))
    else:
        return HttpResponseRedirect('login')


#data handles requests for the visualization page
#studynumber is required to be a valid GSE id of hte form GSE##### where # is a decimal digit
def data(request, studynumber):
    if request.user.is_authenticated():
        #send http response back to user
        t = loader.get_template('index.html')
        c = RequestContext(request, {'studyid':studynumber})
        return HttpResponse(t.render(c))

    else:
        return HttpResponseRedirect('login')

#list handles requests for the requested studies page
def list(request):

    if request.user.is_authenticated():
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
        return HttpResponseRedirect('../login')

#plist handles requests for the processed studies page
def plist(request):
    
    if request.user.is_authenticated():
        # get list of processed studies
        processedlist = getProcessedStudyList()

        # return http response back to user
        t = loader.get_template('plist.html')
        c = RequestContext(request, {'processedlist':processedlist,})
        return HttpResponse(t.render(c))

    else:
        return HttpResponseRedirect('../login')

#qlist handles requests for the queued studies page
def qlist(request):

    if request.user.is_authenticated():
        #get list of queued studies
        queuedlist = getQueuedStudyList()

        # return http response back to user
        t = loader.get_template('qlist.html')
        c = RequestContext(request, {'queuedlist':queuedlist,})
        return HttpResponse(t.render(c))

    else:
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
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
    
    path = 'Studies/GSE' + studynumber + '/'
    listing = os.listdir(path)
    for file in listing:
        filename = file # Select your files here.                           
        archive.write(path + filename, filename) #studyid = 'filename'
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=GSE' + studynumber + '.zip'
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
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

    path = 'Studies/GSE' + studynumber + 'P/'
    listing = os.listdir(path)
    for file in listing:
        filename = file # Select your files here.
        archive.write(path + filename, filename) #studyid = 'filename'
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=GSE' + studynumber + '-allpairs.zip'
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
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)

    path = 'Studies/GSE' + studynumber + '/'
    filename = 'log.txt' # Select your files here.
    archive.write(path + filename, filename) #studyid = 'filename'
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    name = 'attachment; filename=GSE' + studynumber + '-logfile.zip'
    response['Content-Disposition'] = name
    response['Content-Length'] = temp.tell()
    temp.seek(0)
    return response

#format data handles requests made on the visualization page for Study data and returns them to the applicaton in json format
def formatData(request):
        studyid = request.GET.get('studyid');
        var1 = request.GET.get('gene_x');
        var2 = request.GET.get('gene_y');
        x_data = RetrieveData(studyid,var1)
        y_data = RetrieveData(studyid,var2)
        data = []
        if x_data.count>0 and y_data.count>0:
                for i in xrange(len(x_data)):
                        result = {}
                        result["x"] = x_data[i]
                        result["y"] = y_data[i]
                        data.append(result)
        return HttpResponse(simplejson.dumps({"data": data}),mimetype="application/json")
