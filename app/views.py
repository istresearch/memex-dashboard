import json

from elasticsearch import Elasticsearch 
from elasticsearch.client import IndicesClient
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.shortcuts import get_current_site

import settings

def index(request):
    response = { 'site': get_current_site(request), 'domains': [] }
    client = IndicesClient(Elasticsearch(settings.ELASTICSEARCH['hosts']))
    for idx in client.get(index=settings.ELASTICSEARCH['index'], feature='_mappings'):
        mappings =  client.get(index=settings.ELASTICSEARCH['index'], feature='_mappings')[idx]['mappings']
        for mapping in mappings:
            response['domains'].append(mapping)
    return render(request, 'app/index.html', response)

@csrf_exempt
def query(request):
    response = {}
    if request.method == 'POST':
        body = json.loads(request.body)
        client = Elasticsearch(settings['elasticsearch']['hosts'])
        response = client.search(index=settings['elasticsearch']['index'], body=body)
    return HttpResponse(json.dumps(response), 'application/json')

def get(request, _type, _id):
    response = {}
    client = Elasticsearch(settings['elasticsearch']['hosts'])
    response = client.get(index=settings['elasticsearch']['index'], doc_type=_type, id=_id)
    return HttpResponse(json.dumps(response), 'application/json')


def domain(request, _domain):
    response = {}
    _filter = { "domain": _domain }
    response['domain'] = _domain
    response['hosts'] = _aggregate("url.hostname", filter=_filter)
    return render(request, 'app/domain.html', response)
    
    

# TODO: Move helpers to their own modules


def _aggregate(field, size=10, filter=None):
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])
    body = { "size": 0, "aggs" : { "_agg" : { "terms" : { "field" : field, "size": size } } } }
    if filter is not None:
        body["filter"] = { "term": filter }
    response = client.search(index=settings.ELASTICSEARCH['index'], body=body)
    return response["aggregations"]["_agg"]
