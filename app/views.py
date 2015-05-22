import json
from elasticsearch import Elasticsearch

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt

settings = {
    'elasticsearch': {
        'hosts': [
            "in-slave01.nj.istresearch.com", 
            "in-slave02.nj.istresearch.com",
            "in-slave03.nj.istresearch.com", 
            "in-slave04.nj.istresearch.com",
            "in-slave05.nj.istresearch.com", 
            "in-slave06.nj.istresearch.com",
            "in-slave07.nj.istresearch.com", 
            "in-slave08.nj.istresearch.com",
        ],
        'index': 'memex'
    }
}

RESPONSE_DEFAULTS = {
    'site': {
        'name':'Memex Dashboard'
    }
}

def index(request):
    response = RESPONSE_DEFAULTS
    response['domains'] = _aggregate("attrs.domain", size=0)
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
    response = RESPONSE_DEFAULTS
    _filter = { "domain": _domain }
    response['domain'] = _domain
    response['hosts'] = _aggregate("response.server.hostname", filter=_filter)
    return render(request, 'app/domain.html', response)
    
    

# TODO: Move helpers to their own modules

def _aggregate(field, size=10, filter=None):
    client = Elasticsearch(settings['elasticsearch']['hosts'])
    body = { "size": 0, "aggs" : { "_agg" : { "terms" : { "field" : field, "size": size } } } }
    if filter is not None:
        body["filter"] = { "term": filter }
    response = client.search(index=settings['elasticsearch']['index'], body=body)
    return response["aggregations"]["_agg"]
