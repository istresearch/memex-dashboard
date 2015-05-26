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
    response['domains'] = _facet("_type", size=0)
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
    response["id"] = response["_id"]
    del response["_id"]
    response["type"] = response["_type"]
    del response["_type"]
    response["source"] = response["_source"]
    del response["_source"]
    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/get.html', response)

def domain(request, _domain):
    response = {}
    _filter = { }
    fa = request.GET.get('f', '')
    if len(fa):
        for fb in fa.split(','):
            fc = fb.split(':')
            _filter[fc[0]] = fc[1]
    if not _filter:
        _filter = None
    docs = int(request.GET.get('d', 10))
    offset = int(request.GET.get('o', 0))
    response['domains'] = _facet("_type", size=0)
    response['domain'] = _domain
    response['filter'] = _filter
    response['teams'] = _facet("team", filter=_filter, domain=_domain)
    response['crawlers'] = _facet("crawler", filter=_filter, domain=_domain)
    response['sites'] = _facet("url.domain", filter=_filter, domain=_domain, size=0, docs=docs, offset=offset)
    response['has_prev'] = offset > 0
    response['has_next'] = offset + docs < response['sites']['doc_count']
    first = offset + 1
    last = offset + len(response['sites']['docs'])
    response['pageinfo'] = { 'first': first, 'last': last, 'total': response['sites']['doc_count'] }
    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/domain.html', response)
    

# TODO: Move helpers to their own modules


def _facet(field, filter=None, domain=None, size=10, docs=0, offset=0):
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])
    body = { 
        "filter": { },
        "aggs" : { "outer" : { "filter": { }, "aggs": { "_agg": { "terms" : { "field" : field, "size": size } } } } },
        "partial_fields" : { "source" : { "exclude" : "content" } },
        "size": docs, 
        "from": offset,
        "sort" : [ { "timestamp" : {"order" : "desc"} } ],
    }
    if filter is not None:
        body["filter"] = { "term": filter }
        body["aggs"]["outer"]["filter"] = { "term": filter }
    response = client.search(index=settings.ELASTICSEARCH['index'], doc_type=domain, body=body)
    count = response["aggregations"]["outer"]["doc_count"]
    for bucket in response["aggregations"]["outer"]["_agg"]["buckets"]:
        count -= bucket["doc_count"]
    count -= response["aggregations"]["outer"]["_agg"]["sum_other_doc_count"]
    if count:
        response["aggregations"]["outer"]["_agg"]["sum_none_doc_count"] = count 
    docs = []
    for doc in response['hits']['hits']:
        doc['id'] = doc['_id']
        del doc['_id']
        doc['type'] = doc['_type']
        del doc['_type']
        docs.append(doc)
    return { "facet": response["aggregations"]["outer"]["_agg"], "docs": response["hits"]["hits"], "doc_count": response["hits"]["total"]}
