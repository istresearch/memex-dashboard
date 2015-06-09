from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^/?$', 'app.views.index'),
    url(r'^get/(?P<_type>.+)/(?P<_id>.+)/?$', 'app.views.get'),
    url(r'^search/?$', 'app.views.search'),
)
