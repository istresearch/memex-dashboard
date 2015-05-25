import json

from elasticsearch import Elasticsearch 
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.shortcuts import get_current_site

import settings

def index(request):
    response = { 'site': get_current_site(request), 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])
    response['domains'] = _aggregate("_type", size=0)
    return render(request, 'app/index.html', response)

@csrf_exempt
def query(request):
    response = {}
    if request.method == 'POST':
        body = json.loads(request.body)
        client = Elasticsearch(settings.ELASTICSEARCH['hosts'])
        response = client.search(index=settings.ELASTICSEARCH['index'], body=body)
    return HttpResponse(json.dumps(response), 'application/json')

def get(request, _type, _id):
    response = {}
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])
    response = client.get(index=settings.ELASTICSEARCH['index'], doc_type=_type, id=_id)
    return HttpResponse(json.dumps(response), 'application/json')

def domain(request, _domain):
    response = {}
    _filter = { '_type': _domain }
    response['domain'] = _domain
    response['hosts'] = _aggregate("url.hostname", filter=_filter)
    response['teams'] = _aggregate("team", filter=_filter)
    response['crawlers'] = _aggregate("crawler", filter=_filter)
    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/domain.html', response)
    

# TODO: Move helpers to their own modules


def _aggregate(field, size=10, filter=None):
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])
    body = { "size": 0, "aggs" : { "_agg" : { "terms" : { "field" : field, "size": size } } } }
    if filter is not None:
        body["filter"] = { "term": filter }
    response = client.search(index=settings.ELASTICSEARCH['index'], body=body)
    count = response["hits"]["total"]
    for bucket in response["aggregations"]["_agg"]["buckets"]:
        count -= bucket["doc_count"]
    count -= response["aggregations"]["_agg"]["sum_other_doc_count"]
    if count:
        response["aggregations"]["_agg"]["sum_none_doc_count"] = count 
    return response["aggregations"]["_agg"]
