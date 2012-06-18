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
    url(r'^studies/GSE(?P<studynumber>\d+)/$', 'application.views.data'),
    url(r'^studies/list/$', 'application.views.list'),
    url(r'^studies/submitted/$', 'application.view.thanks'),
    url(r'^studies/plist/$', 'application.views.plist'),
    url(r'^studies/qlist/$', 'application.views.qlist'),
    url(r'^studies/about/$', 'application.views.about'),
    url(r'^studies/download/GSE(?P<studynumber>\d+)/$', 'application.views.send_zipfile'),
    url(r'^studies/getData/$', 'application.views.formatData'),
    url(r'^studies/downloadAllPairs/GSE(?P<studynumber>\d+)/$', 'application.views.sendAllPairs'),
    url(r'^studies/downloadLog/GSE(?P<studynumber>\d+)/$', 'application.views.sendLog'),
    url(r'^studies/login/$', 'application.views.login_auth'),
)
