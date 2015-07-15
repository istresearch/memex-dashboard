from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('',
    url(r'^/?$', 'app.views.index'),
    url(r'^search/?$', 'app.views.search'),
    url(r'^(?P<_type>[^/]+)/?$', 'app.views.domain'),
    url(r'^(?P<_type>.+)/analysis/?$', 'app.views.analysis'),
    url(r'^(?P<_type>.+)/keyword/?$', 'app.views.keyword'),
    url(r'^get/(?P<_type>.+)/(?P<_id>.+)/?$', 'app.views.get'),
)
