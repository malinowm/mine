from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'myproject.views.home', name='home'),
    # url(r'^myproject/', include('myproject.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^studies/$', 'application.views.home'),
    #url(r'^studies/view/GSE(?P<studynumber>\d+)/$', 'application.views.data'),
    url(r'^studies/view/(?P<studynumber>\w+)/$', 'application.views.data'),
    url(r'^studies/list/$', 'application.views.list'),
    url(r'^studies/submitted/$', 'application.view.thanks'),
    url(r'^studies/plist/$', 'application.views.plist'),
    url(r'^studies/qlist/$', 'application.views.qlist'),
    url(r'^studies/about/$', 'application.views.about'),
   # url(r'^studies/download/GSE(?P<studynumber>\d+)/$', 'application.views.send_zipfile'),
    url(r'^studies/download/(?P<studynumber>\w+)/$', 'application.views.send_zipfile'),
    url(r'^studies/getData/$', 'application.views.formatData'),
    #url(r'^studies/downloadAllPairs/GSE(?P<studynumber>\d+)/$', 'application.views.sendAllPairs'),
    url(r'^studies/downloadAllPairs/(?P<studynumber>\w+)/$', 'application.views.sendAllPairs'),
    #url(r'^studies/downloadLog/GSE(?P<studynumber>\d+)/$', 'application.views.sendLog'),
    url(r'^studies/downloadLog/(?P<studynumber>\w+)/$', 'application.views.sendLog'),
    url(r'^studies/login/$', 'application.views.login_auth'),
    url(r'^studies/admin/$', 'application.views.admin'),
    url(r'^studies/adminlog/$', 'application.views.sendadminLog'),
    #url(r'^studies/sendStudy/GSE(?P<studyid>\d+)/$', 'application.views.sendStudy'),
    url(r'^studies/sendStudy/(?P<studyid>\w+)/$', 'application.views.sendStudy'),
    url(r'^studies/ac/$', 'application.views.complete'),
    url(r'^studies/geneExists/$', 'application.views.geneExistance'),
    url(r'^studies/getChartData/$', 'application.views.getChartData'),
    url(r'^studies/upload/$', 'application.views.upload_study'),
    url(r'^studies/downloadsamples/$', 'application.views.get_samples'),
    url(r'^studies/getAttrData/$', 'application.views.getAttrData'),
    url(r'^studies/studyerror/$', 'application.views.studyerror'),
)


