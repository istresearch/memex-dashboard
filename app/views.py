import json

from urllib2 import urlparse
from bs4 import BeautifulSoup as bs
from elasticsearch import Elasticsearch 
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.shortcuts import get_current_site

import settings

def index(request):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])

    response['domains'] = _facet(client, '_type')

    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/index.html', response)

def get(request, _type, _id):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])

    response['domains'] = _facet(client, '_type')
    
    doc = client.get(index=settings.ELASTICSEARCH['index'], doc_type=_type, id=_id)
    doc['id'] = doc.pop('_id')
    doc['type'] = doc.pop('_type')
    doc['source'] = doc.pop('_source')
    doc['index'] = doc.pop('_index')
    doc['version'] = doc.pop('_version')

    #try:
    url = doc['source']['url']
    if doc['source']['raw_content']:
            soup = bs(doc['source']['raw_content'], 'html.parser')
            images = soup.find_all('img')
            imglist = []
            for image in images:
                try:
                    imglist.append(urlparse.urljoin(url, image.get('src')))
                except:
                    imglist.append(urlparse.urljoin(url[0], image.get('src')))
            try:
                doc['source']['crawl_data']['images'] = imglist
            except:
                doc['source']['crawl_data'] = {}
                doc['source']['crawl_data']['images'] = imglist
    #except:
    #    pass

    response['doc'] = doc

    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/get.html', response)

@csrf_exempt
def search(request):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])

    response['domains'] = _facet(client, '_type')

    page = int(request.POST.get('page', 0))
    pagesize = int(request.POST.get('pagesize', 10))
    filter = {}
    filter['domain'] = request.POST.get('domain')
    filter['site'] = request.POST.get('site')
    filter['team'] = request.POST.get('team')
    filter['crawler'] = request.POST.get('crawler')
    filter['phrase'] = request.POST.get('phrase', '').replace('+', ' ')
    filter['exact'] = 'true' if request.POST.get('exact') == 'true' else 'false'
    filter['docs'] = pagesize
    filter['offset'] = page * pagesize
    response['filter'] = filter
    
    response['teams'] = _facet(client, 'team', filter['domain'])
    response['crawlers'] = _facet(client, 'crawler', filter['domain'])

    _filter = {}
    _and = [] 
    if filter['team']:
        _and.append({ 'term': {'team': filter['team'] } })
    if filter['crawler']:
        _and.append({ 'term': {'crawler': filter['crawler'] } })
    if filter['site']:
        _and.append({ 'term': {'url.domain': filter['site'] } })
    if len(_and):
        _filter = { 'and': _and }
    
    response['sites'] = _facet(client, 'url.domain', filter['domain'], _filter)
    
    _query = {}
    if filter['phrase']:
        query_type = 'match_phrase' if filter['exact'] == 'true' else 'match'
        _query = { query_type: { 'raw_content': filter['phrase'] } }
    
    docs = _search(client, filter['domain'], _query, _filter, filter['docs'], filter['offset'])
    response['docs'] = docs['hits']['hits']
    response['total'] = docs['hits']['total']
    response['first'] = filter['offset'] + 1
    response['last'] = filter['offset'] + filter['docs']
    response['has_prev'] = filter['offset'] > 0
    response['has_next'] = filter['offset'] + filter['docs'] < docs['hits']['total']    
    
    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/search.html', response)
    
def _facet(client, field, type=None, filter={}, size=0):    

    request = { 
        'filter': filter,
        'aggs' : { 'outer' : { 'filter': filter, 'aggs': { 'inner': { 'terms' : { 'field' : field, 'size': size } } } } },
        'partial_fields' : { 'source' : { 'exclude' : 'raw_content,crawl_data' } },
    }
    
    data = client.search(index=settings.ELASTICSEARCH['index'], doc_type=type, body=request)
    
    count = data['aggregations']['outer']['doc_count']
    for bucket in data['aggregations']['outer']['inner']['buckets']:
        count -= bucket['doc_count']
    count -= data['aggregations']['outer']['inner']['sum_other_doc_count']
    if count:
        data['aggregations']['outer']['inner']['sum_none_doc_count'] = count 
    
    return data['aggregations']['outer']['inner']

def _search(client, domain, query={}, filter={}, docs=0, offset=0):

    data = { 
        'partial_fields' : { 'source' : { 'exclude' : 'raw_content,crawl_data' } },
        'size': docs, 
        'from': offset,
        'sort' : [ { 'timestamp' : {'order' : 'desc'} } ],
    }   
     
    if len(filter) and not len(query):
        data['filter'] = filter
    if len(query) and not len(filter):
        data['query'] = query
    if len(filter) and len(query):
        data['query'] = { 'filtered': { 'query': query, 'filter': filter } }
    
    response = client.search(index=settings.ELASTICSEARCH['index'], doc_type=domain, body=data)
    for doc in response['hits']['hits']:
        doc['id'] = doc.pop('_id')
        doc['type'] = doc.pop('_type')
        doc['score'] = doc.pop('_score')
        doc['index'] = doc.pop('_index')
    return response
    
