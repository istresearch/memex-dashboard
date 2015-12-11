import json
import csv
import os
import time 
import settings
import subprocess
import sys
from models import Url_Note
from models import Sections_Scraping
from urllib2 import urlparse
from bs4 import BeautifulSoup as bs
from elasticsearch import Elasticsearch 
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sites.shortcuts import get_current_site
from django.core import serializers
from os import listdir
from os.path import isfile, join
from dateutil import parser
#from sql import *

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

    crawl_data = doc['source'].get('crawl_data')
    if crawl_data:
        doc['crawl_data_json'] = json.dumps(crawl_data, indent=4)

    response['doc'] = doc

    _format = request.GET.get('format', '')
    if _format == 'json':
        return HttpResponse(json.dumps(response), 'application/json')
    #return HttpResponse(json.dumps(response), 'application/json')
    return render(request, 'app/get.html', response)

def report(request):

    _url = request.GET.get('url')
    _note = request.GET.get('note')
    _sections_scraping = request.GET.get('sectionsScraping')
    _archiveRequest = request.GET.get('datetime', '')
    _domain = request.GET.get('domain', '')
    
    if _url: 
        if _sections_scraping is not None:   
            try:
                ss = Sections_Scraping.objects.get(url=_url)
                ss.sections_scraping = _sections_scraping
            except:
                ss = Sections_Scraping(url=_url, sections_scraping=_sections_scraping)
            ss.save()
        if _note:
            note = Url_Note(url=_url, note=_note)
            note.save()
        params = ''
        if _archiveRequest != '':
            params += '?datetime=' + _archiveRequest
        if _domain != '': 
            if params != '':
                params += '&domain=' + _domain
            else:
                params += '?domain=' + _domain
        return HttpResponseRedirect("/memex-dashboard/report" + params)
         
    response = { 'site': get_current_site(request).name, 'domains': [] }
    client = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)
    response['domains'] = _facet(client, '_type')

    reportGenScript = settings.SCRIPTS_DIR + 'domain-stats-report-gen.py'
    reportName = settings.CRAWL_REPORT_NAME_DEFAULT
    reportDirectory = settings.CRAWL_REPORT_DIRECTORY
    reportLocation = reportDirectory + reportName
    fileSuffix = ".csv"  

    sections_scraping = serializers.serialize('json', Sections_Scraping.objects.all(), fields=('url', 'sections_scraping', 'timestamp'))
    notes = serializers.serialize('json', Url_Note.objects.all(), fields=('url','note', 'timestamp', 'user'))

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
            retcode = generateReport(reportLocation, _domain)
    elif _domain != '':
        reportDirectory += _domain + '/'
        if not os.path.exists(reportDirectory):
            os.makedirs(reportDirectory)
        reportName = 'CDR-Stats-' + time.strftime("%Y-%m-%d_%H%M%S") + "-" + _domain + fileSuffix
        reportLocation = reportDirectory + reportName
        retcode = generateReport(reportLocation, _domain, notes, sections_scraping)
    else:
        reportName = 'CDR-Stats-' + time.strftime("%Y-%m-%d_%H%M%S") + fileSuffix
        reportLocation = reportDirectory + reportName
        retcode = generateReport(reportLocation, _domain)
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
def generateReport(reportLocation, _domain, notes, sections_scraping):
    outputFile = os.environ.get('CRAWL_REPORT_NAME_DEFAULT', 'domain_stats_report.csv')
    domain = ''
    outputFile = reportLocation

    es = Elasticsearch(settings.ELASTICSEARCH['hosts'], timeout=ELASTICSEARCH_TIMEOUT)
    query = {"aggs": {"by_domain": {"terms": {"field": "url.domain", "size": 0}, "aggs": {"by_type": {"terms": {"field": "_type", "size": 0}, "aggs": {"last_30_days": {"filter": {"range": {"timestamp": {"gt": now - 30 * 86400 * 1000}}}}, "imported": {"filter": {"bool": {"must": {"term": {"imported": "true"}}}}}, "last_90_days": {"filter": {"range": {"timestamp": {"gt": now - 60 * 86400 * 1000}}}}, "imported_within_90_days": {"filter": {"range": {"imported_ts": {"gt": now - 60 * 86400 * 1000}}}}, "scraped_since": {"min": {"field": "timestamp", "format": "yyyy-MM-dd"}}, "postings_count": {"value_count": {"field": "url"}}, "last_60_days": {"filter": {"range": {"timestamp": {"gt": now - 30 * 86400 * 1000}}}}, "ic3": {"value_count": {"field": "crawl_data.attributes.images.url"}}, "ic2": {"value_count": {"field": "images"}}, "ic1": {"value_count": {"field": "crawl_data.images"}}}}}}}}
    print query
    all_domains = {}
    if _domain:
        all_domains = es.search(index=os.environ.get('ES_INDEX', 'memex'), doc_type=_domain, body=query)
    else:
        all_domains = es.search(index=os.environ.get('ES_INDEX', 'memex'), body=query)

    field_names = ['domain', 'source_type', 'url', 'currently_scraping', 'currently_importing',
                   'sections_scraping', 'scraped_since', 'all_postings', 'distinct_documents',
                   'last_30_days', 'last_60_days', 'last_90_days', 'number_of_images', 'notes']

    f = open(outputFile, 'w+')
    csv_file = csv.DictWriter(
        f, fieldnames=field_names, restval='', dialect='excel')
    csv_file.writeheader()

    tot_postings, tot_docs, tot_images, tot_30, tot_60, tot_90, tot_scraping, tot_importing = 0, 0, 0, 0, 0, 0, 0, 0

    allNotes = json.loads(notes)
    allSectionsScraping = json.loads(sections_scraping)

    for item in all_domains['aggregations']['by_domain']['buckets']:
        for typed_item in item['by_type']['buckets']:
            scrapedSince = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(typed_item['scraped_since']['value'] / 1000))
            tot_postings += typed_item['postings_count']['value']
            tot_docs += typed_item['doc_count']
            imageCount = typed_item['ic1']['value']
            imageCount += typed_item['ic2']['value']
            imageCount += typed_item['ic3']['value']
            tot_images += imageCount
            tot_30 += typed_item['last_30_days']['doc_count']
            tot_60 += typed_item['last_60_days']['doc_count']
            tot_90 += typed_item['last_90_days']['doc_count']
            scraping = 'Yes' if typed_item['last_90_days']['doc_count'] > 0 else 'No'
            importing = 'Yes' if typed_item['imported_within_90_days']['doc_count'] > 0 else 'No'
            tot_scraping += 1 if scraping == 'Yes' else 0
            tot_importing += 1 if importing == 'Yes' else 0
            url = FULL_URLS[item['key']] if item['key'] in FULL_URLS else item['key']
            note = ""
            sectionsScraping = ""
            for ss in allSectionsScraping: 
                if ss['fields']['url'].strip() == url:
                    sectionsScraping = ss['fields']['sections_scraping']
            for f in allNotes:
                if f['fields']['url'].strip() == url:
                    note += f['fields']['note'] + "\n *************** \n "
            csv_file.writerow({'domain': typed_item['key'],
                               'source_type': 'Ads',
                               'url': url,
                               'currently_scraping': scraping,
                               'currently_importing': importing,
                               'sections_scraping': sectionsScraping,
                               'scraped_since': scrapedSince,
                               'all_postings': typed_item['postings_count']['value'],
                               'distinct_documents': typed_item['doc_count'],
                               'last_30_days': typed_item['last_30_days']['doc_count'],
                               'last_60_days': typed_item['last_60_days']['doc_count'],
                               'last_90_days': typed_item['last_90_days']['doc_count'],
                               'number_of_images': imageCount,
                               'notes': note})
    csv_file.writerow({'domain': 'TOTALS',
                       'source_type': '',
                       'url': '',
                       'currently_scraping': tot_scraping,
                       'currently_importing': tot_importing,
                       'sections_scraping': '',
                       'scraped_since': '',
                       'all_postings': tot_postings,
                       'distinct_documents': tot_docs,
                       'last_30_days': tot_30,
                       'last_60_days': tot_60,
                       'last_90_days': tot_90,
                       'number_of_images': tot_images,
                       'notes': ''})
    #f.close()

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

#See ticket MEM-681; this is a temporary workaround 
FULL_URLS = {
    "com.au": "craigslist.com.au",
    "com.br": "foxbit.com.br",
    "co.uk": "craigslist.co.uk",
    "co.th": "craigslist.co.th",
    "co.nz": "craigslist.co.nz",
    "com.sg": "craigslist.com.sg",
    "co.kr": "craigslist.co.kr",
    "com.tw": "craigslist.com.tw",
    "com.ph": "craigslist.com.ph",
    "co.za": "craigslist.co.za",
    "com.mx": "craigslist.com.mx",
    "co.in": "craigslist.co.in",
    "com.tr": "craigslist.com.tr",
    "com.cn": "craigslist.com.cn",
    "org.cn": "isp.org.cn",
    "-632.com": "K-632.com"
}


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
