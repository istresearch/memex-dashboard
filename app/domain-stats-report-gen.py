#!/usr/bin/env python
import json
from elasticsearch import Elasticsearch
import logging
import sys
import csv
import time
import os
import settings
from addict import Dict

now = time.time() * 1000

log = logging.getLogger(__name__)

#See ticket MEM-681; this is a temporary workaround 
full_urls = {
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

outputFile = os.environ.get('CRAWL_REPORT_NAME_DEFAULT', 'domain_stats_report.csv')
domain = ''
if len(sys.argv) > 1:
    outputFile = sys.argv[1]

log.info("Connect to ES")
#es = Elasticsearch(os.environ.get('ES_HOSTS', 'localhost').split(','))
es = Elasticsearch(settings.ELASTICSEARCH['hosts'])
query = Dict()
#query = '{ "query": { "match_all": {} } }'

#query.aggs.by_domain.terms.field = "url.domain"
#query.aggs.by_domain.terms.size = 0
#query.aggs.by_domain.aggs.by_type.terms.field = "_type"
#query.aggs.by_domain.aggs.by_type.terms.size = 0
#query.aggs.by_domain.aggs.by_type.aggs.ic1 = {"value_count": {"field": "crawl_data.images"} }
#query.aggs.by_domain.aggs.by_type.aggs.ic2 = {"value_count": {"field": "images"} }
#query.aggs.by_domain.aggs.by_type.aggs.ic3 = {"value_count": {"field": "crawl_data.attributes.images.url"} }
#query.aggs.by_domain.aggs.by_type.aggs.postings_count = {"value_count": {"field": "url"} }
#query.aggs.by_domain.aggs.by_type.aggs.scraped_since = {"min": {"field": "timestamp", "format" : "yyyy-MM-dd" } }
#query.aggs.by_domain.aggs.by_type.aggs.imported.filter = {"bool": {"must": {"term": {"imported": "true"}}}}
#query.aggs.by_domain.aggs.by_type.aggs.last_30_days.filter = {"range": { "timestamp": { "gt": now - 30 * 86400 * 1000}}}
#query.aggs.by_domain.aggs.by_type.aggs.last_60_days.filter = {"range": { "timestamp": { "gt": now - 60 * 86400 * 1000}}}
#query.aggs.by_domain.aggs.by_type.aggs.last_90_days.filter = {"range": { "timestamp": { "gt": now - 90 * 86400 * 1000}}}

#print query

query = {"aggs": {"by_domain": {"terms": {"field": "url.domain", "size": 0}, "aggs": {"by_type": {"terms": {"field": "_type", "size": 0}, "aggs": {"last_30_days": {"filter": {"range": {"timestamp": {"gt": now - 30 * 86400 * 1000}}}}, "imported": {"filter": {"bool": {"must": {"term": {"imported": "true"}}}}}, "last_90_days": {"filter": {"range": {"timestamp": {"gt": now - 60 * 86400 * 1000}}}}, "imported_within_90_days": {"filter": {"range": {"imported_ts": {"gt": now - 60 * 86400 * 1000}}}}, "scraped_since": {"min": {"field": "timestamp", "format": "yyyy-MM-dd"}}, "postings_count": {"value_count": {"field": "url"}}, "last_60_days": {"filter": {"range": {"timestamp": {"gt": now - 30 * 86400 * 1000}}}}, "ic3": {"value_count": {"field": "crawl_data.attributes.images.url"}}, "ic2": {"value_count": {"field": "images"}}, "ic1": {"value_count": {"field": "crawl_data.images"}}}}}}}}

#query = {"aggs": {"by_domain": {"terms": {"field": "url.domain", "size": 0 } } } }

print query

#query = '{ "query": { "match_all": {} } }'

print 'sysargv2: '
#log.error('arguments: ' + sys.argv[1] + ' ' + sys.argv[2])
all_domains = {}
#if len(sys.argv) > 2:
    #all_domains = es.search(index=os.environ.get('ES_INDEX', 'memex'), doc_type=sys.argv[2], body=query)
all_domains = es.search(index='memex-domains', doc_type=sys.argv[2], body=query)
#else:
    #all_domains = es.search(index=os.environ.get('ES_INDEX', 'memex'), body=query)
    #all_domains = es.search(index=settings.ELASTICSEARCH['index'], body=query)
log.debug(json.dumps(all_domains, indent=4))

field_names = ['domain', 'source_type', 'url', 'currently_scraping', 'currently_importing',
               'sections_scraping', 'scraped_since', 'all_postings', 'distinct_documents',
               'number_of_images', 'last_30_days', 'last_60_days', 'last_90_days']

f = open(outputFile, 'w+')
csv_file = csv.DictWriter(
    f, fieldnames=field_names, restval='', dialect='excel')
csv_file.writeheader()

tot_postings, tot_docs, tot_images, tot_30, tot_60, tot_90, tot_scraping, tot_importing = 0, 0, 0, 0, 0, 0, 0, 0

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
        url = full_urls[item['key']] if item['key'] in full_urls else item['key']
        csv_file.writerow({'domain': typed_item['key'],
                           'source_type': 'Ads',
                           'url': url,
                           'currently_scraping': scraping,
                           'currently_importing': importing,
                           'sections_scraping': '',
                           'scraped_since': scrapedSince,
                           'all_postings': typed_item['postings_count']['value'],
                           'distinct_documents': typed_item['doc_count'],
                           'number_of_images': imageCount,
                           'last_30_days': typed_item['last_30_days']['doc_count'],
                           'last_60_days': typed_item['last_60_days']['doc_count'],
                           'last_90_days': typed_item['last_90_days']['doc_count']})

csv_file.writerow({'domain': 'TOTALS',
                   'source_type': '',
                   'url': '',
                   'currently_scraping': tot_scraping,
                   'currently_importing': tot_importing,
                   'sections_scraping': '',
                   'scraped_since': '',
                   'all_postings': tot_postings,
                   'distinct_documents': tot_docs,
                   'number_of_images': tot_images,
                   'last_30_days': tot_30,
                   'last_60_days': tot_60,
                   'last_90_days': tot_90})

f.close()

log.debug(json.dumps(query, indent=4))

sys.exit(1)
