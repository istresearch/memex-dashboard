from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^/?$', 'app.views.index'),

    url(r'^query/?$', 'app.views.query'),
    url(r'^get/(?P<_type>.+)/(?P<_id>.+)/?$', 'app.views.get'),

    url(r'^domain/(?P<_domain>.+)/search/?$', 'app.views.search'),
    url(r'^domain/(?P<_domain>.+)/?$', 'app.views.domain'),
)
