try:
    from django.conf.urls import patterns, include
except ImportError:
    from django.conf.urls.defaults import patterns, include

from django.contrib import admin
admin.autodiscover()

# Be sure to autodiscover the reports
import reportengine
reportengine.autodiscover()

urlpatterns = patterns(
    '',
    (r'^$', 'django.views.generic.simple.redirect_to', {"url": "/reports/"}),
    (r'^admin/', include(admin.site.urls)),
    (r'^reports/', include('reportengine.urls')),
)

