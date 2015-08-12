import json
import csv
import os
import time 
import settings

from urllib2 import urlparse
from bs4 import BeautifulSoup as bs
from elasticsearch import Elasticsearch 
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.shortcuts import get_current_site
from os import listdir
from os.path import isfile, join
from dateutil import parser

now = time.time() * 1000

DATE_RANGES = { 
    'hour': now - 3600 * 1000, 
    'day': now - 86400 * 1000, 
    'week': now - 7 * 86400 * 1000,
    'month': now - 30 * 86400 * 1000,
    'year': now - 365 * 86400 * 1000,
}

ELASTICSEARCH_TIMEOUT = 60

def index(request):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)

    response['domains'] = _facet(client, '_type')

    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/index.html', response)

def domain(request, _type):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)

    response['domains'] = _facet(client, '_type')

    page = int(request.POST.get('page', 0))
    pagesize = int(request.POST.get('pagesize', 50))
    filter = {}
    filter['domain'] = _type
    filter['site'] = request.POST.get('site')
    filter['team'] = request.POST.get('team')
    filter['crawler'] = request.POST.get('crawler')
    filter['timestamp'] = request.POST.get('timestamp')
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
    if filter['timestamp']:
        _and.append({ 'range': {'timestamp': { 'gte': DATE_RANGES[filter['timestamp']] } } })
    if len(_and):
        _filter = { 'and': _and }
    
    response['sites'] = _facet(client, 'url.domain', filter['domain'], _filter)
    response['dates'] = _ranges(client, filter['domain'])
    
    _query = {}
    if filter['phrase']:
        query_type = 'match_phrase' if filter['exact'] == 'true' else 'match'
        _query = { query_type: { 'raw_content': filter['phrase'] } }
    
    docs = _search(client, filter['domain'], _query, _filter, filter['docs'], filter['offset'])
    response['docs'] = docs['hits']['hits']
    response['total'] = docs['hits']['total']
    response['first'] = filter['offset'] + 1
    response['last'] = min(filter['offset'] + filter['docs'], docs['hits']['total'])
    response['has_prev'] = filter['offset'] > 0
    response['has_next'] = filter['offset'] + filter['docs'] < docs['hits']['total']    
    
    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/domain.html', response)

def analysis(request, _type):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)
    
    response['domain'] = _type
    response['domains'] = _facet(client, '_type')
    response['keywords'] = KEYWORDS.get(_type, [])

    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/analysis.html', response)

def keyword(request, _type,):
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)

    size = request.GET.get('size', 10)
    keyword = request.GET.get('keyword', '')
    data = _facet(client, 'url.domain', type=_type, filter={ "bool": { "must": { "query": { "match_phrase": { "raw_content": keyword } } } } }, size=size, filter_all=False)
    response = {
        'keyword': keyword,
        'all': data['total'],
        'matched': data['sum_other_doc_count'],
        'sites': {},
        'other': data['sum_other_doc_count'],
    }
    for bucket in data['buckets']:
        response['sites'][bucket['key']] = bucket['doc_count']
        response['matched'] += bucket['doc_count']

    return HttpResponse(json.dumps(response), 'application/json')

def get(request, _index, _type, _id):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)

    response['domains'] = _facet(client, '_type')
    
    doc = client.get(index=_index, doc_type=_type, id=_id)
    doc['id'] = doc.pop('_id')
    doc['type'] = doc.pop('_type')
    doc['source'] = doc.pop('_source')
    doc['index'] = doc.pop('_index')
    doc['version'] = doc.pop('_version')

    #try:
    '''
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
    '''
    crawl_data = doc['source'].get('crawl_data')
    if crawl_data:
        doc['crawl_data_json'] = json.dumps(crawl_data, indent=4)
    #except:
    #    pass

    response['doc'] = doc

    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/get.html', response)

def report(request):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'])
    response['domains'] = _facet(client, '_type')

    _archiveRequest = request.GET.get('datetime', '')
    _domain = request.GET.get('domain', '')

    reportGenScript = settings.SCRIPTS_FOLDER + 'domain-stats-report-gen.py'
    reportName = settings.CRAWL_REPORT_NAME_DEFAULT
    reportDirectory = settings.CRAWL_REPORT_DIRECTORY
    reportLocation = reportDirectory + reportName
    fileSuffix = ".csv"
    if _archiveRequest != '':
        if _domain != '':
            reportDirectory += _domain + '/'
            fileSuffix = "-" + _domain + fileSuffix
        files = [f[10: 27] for f in listdir(reportDirectory) if isfile(join(reportDirectory,f)) ]
        if len(files) > 0:
            _archiveRequest = time.strptime(_archiveRequest, '%Y-%m-%d_%I%p')
            _archiveRequest = time.strftime('%Y-%m-%d_%H%M%S', _archiveRequest)
            files.sort()
            for f in files:
                if _archiveRequest <= f:
                    reportName = 'CDR-Stats-' + f + fileSuffix
                    break
            files.append(_archiveRequest)
            reportLocation = reportDirectory + reportName
            os.system("python " + reportGenScript + " " + reportLocation + " " + _domain)
    elif _domain != '':
        reportDirectory += _domain + '/'
        if not os.path.exists(reportDirectory):
            os.makedirs(reportDirectory)
        reportName = 'CDR-Stats-' + time.strftime("%Y-%m-%d_%H%M%S") + "-" + _domain + fileSuffix
        reportLocation = reportDirectory + reportName
        os.system("python " + reportGenScript + " " + reportLocation + " " + _domain)
    else:
        reportName = 'CDR-Stats-' + time.strftime("%Y-%m-%d_%H%M%S") + fileSuffix
        reportLocation = reportDirectory + reportName
        os.system("python " + reportGenScript + " " + reportLocation)

    response['domain'] = _domain
    response['reportName'] = reportName

    with open(reportLocation, 'rb') as f:
        reader = csv.reader(f)
        records = list(reader)
        #this expects the TOTALS record to be the last in the report
        totals = records.pop()
        response['totals'] = totals
        #remove csv header row
        records = records[1:]
        response['records'] = records
    f.close()

    return render(request, 'app/report.html', response)

@csrf_exempt
def search(request):
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)

    response['domains'] = _facet(client, '_type')

    page = int(request.POST.get('page', 0))
    pagesize = int(request.POST.get('pagesize', 10))
    filter = {}
    filter['domain'] = request.POST.get('domain')
    filter['site'] = request.POST.get('site')
    filter['team'] = request.POST.get('team')
    filter['crawler'] = request.POST.get('crawler')
    filter['timestamp'] = request.POST.get('timestamp')
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
    if filter['timestamp']:
        _and.append({ 'range': {'timestamp': { 'gte': DATE_RANGES[filter['timestamp']] } } })
    if len(_and):
        _filter = { 'and': _and }
    
    response['sites'] = _facet(client, 'url.domain', filter['domain'], _filter)
    response['dates'] = _ranges(client, filter['domain'])
    
    _query = {}
    if filter['phrase']:
        query_type = 'match_phrase' if filter['exact'] == 'true' else 'match'
        _query = { query_type: { 'raw_content': filter['phrase'] } }
    
    docs = _search(client, filter['domain'], _query, _filter, filter['docs'], filter['offset'])
    response['docs'] = docs['hits']['hits']
    response['total'] = docs['hits']['total']
    response['first'] = filter['offset'] + 1
    response['last'] = min(filter['offset'] + filter['docs'], docs['hits']['total'])
    response['has_prev'] = filter['offset'] > 0
    response['has_next'] = filter['offset'] + filter['docs'] < docs['hits']['total']    
    
    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/search.html', response)

def _ranges(client, type=None):

    ranges = []
    for kk in DATE_RANGES:
        ranges.append({'from': DATE_RANGES[kk], 'key':kk})

    request = { 
        'filter': {},
        'aggs' : { 'outer' : { 'filter': {}, 'aggs': { 'inner': { 
                'date_range': {
                    'field': 'timestamp',
                    'ranges': ranges
                }
        } } } },
        'size': 0
    }
    
    data = client.search(index=settings.ELASTICSEARCH['index'], doc_type=type, body=request)
    
    return data['aggregations']['outer']['inner']
    
def _facet(client, field, type=None, filter={}, size=0, filter_all=True):    

    request = { 
        'filter': {},
        'aggs' : { 'outer' : { 'filter': filter, 'aggs': { 'inner': { 'terms' : { 'field' : field, 'size': size } } } } },
        'partial_fields' : { 'source' : { 'exclude' : 'raw_content,crawl_data' } },
    }

    if filter_all:
        request['filter'] = filter
    
    data = client.search(index=settings.ELASTICSEARCH['index'], doc_type=type, body=request)
    
    data['aggregations']['outer']['inner']['total'] = data['hits']['total']
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

KEYWORDS = {
    'electronics': [
        "Altera ",
        "Microsemi",
        "Actel",
        "Motorola",
        "Freescale",
        "Philips",
        "NXP",
        "TI",
        "Toshiba",
        "Xilinx",
        "AMD",
        "Spansion",
        "Analog Devices",
        "Texas Instr",
        "Austin",
        "Xicor",
        "Intersil",
        "National",
        "National ",
        "TDK",
        "Zilog",
        "Agilent",
        "Avago",
        "Atmel",
        "Burr Brown",
        "Chips",
        "Asiliant",
        "Conexant",
        "Cypress",
        "Fairchild",
        "Harris",
        "Hitachi",
        "ICS",
        "IDT",
        "Linear Tech",
        "Linfinity",
        "SG",
        "Majestic",
        "Malay",
        "Maxim",
        "Microlinear",
        "Microsemi ",
        "ON Semi",
        "OKI",
        "Lapis",
        "Philips or Intersil",
        "Seagate",
        "Sharp",
        "Siliconix",
        "Sipex",
    ],
    "weapons": [
        "Glock Switch",
        "Glock Chip",
        "Chip ",
        "Baffle",
        "Baffle Stack",
        "Monocore",
        "Anarchist",
        "Solvent Trap",
        "LDC",
        "Belt Fed",
        "Crew served",
        "Hip Whip",
        "Polymer",
        "CNC machine",
        "Green tip",
        "Black tip",
        "FAL",
        "Outer tube",
        "trigger"
    ]
}
