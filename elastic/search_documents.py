#!/usr/bin/python
import sys
import base64
from datetime import datetime
from config import es as default_es

def search(field, queryStr, start=0, pageCount=100, fields = [], es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    if len(queryStr) > 0:
        query = {
            "query": {
                "query_string": {
                    "fields" : [field],
                    "query": ' and  '.join(queryStr[0:]),
                }
            },
            "fields": fields
        }

        res = es.search(body=query, index=es_index, doc_type=es_doc_type, from_=start, size=pageCount)
        hits = res['hits']['hits']

        results = []
        for hit in hits:
            fields = hit['fields']
            fields['id'] = hit['_id']
            results.append(fields)

            return {"total": res['hits']['total'], 'results':results}

def multifield_query_search(s_fields, start=0, pageCount=100, fields = [], es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    query = None
    for field, value in s_fields.items():
        if query is None:
            query = "(" + field + ":" + value + ")"
        else:
            query = query + " AND " + "(" + field + ":" + value + ")"

    if not query is None:
        query = {
            "query": {
                "query_string": {
                    "query": query
                }
            },
            "fields": fields
        }

        res = es.search(body=query, index=es_index, doc_type=es_doc_type, from_=start, size=pageCount, request_timeout=600)

        hits = res['hits']['hits']

        results = []
        for hit in hits:
            if hit.get('fields') is None:
                print hit
            else:
                fields = hit['fields']
                fields['id'] = hit['_id']
                results.append(fields)

        return {"total": res['hits']['total'], 'results':results}

def term_search(field, queryStr, start=0, pageCount=100, fields=[], es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    if len(queryStr) > 0:
        query = {
            "query" : {
                "match": {
                    field: {
                        "query": ' '.join(queryStr),
                        "minimum_should_match":"100%"
                    }
                }
            },
            "fields": fields
        }

        res = es.search(body=query, index=es_index, doc_type=es_doc_type, from_=start, size=pageCount)
        hits = res['hits']['hits']

        results = []
        for hit in hits:
            if hit.get('fields') is None:
                print hit
            else:
                fields = hit['fields']
                fields['id'] = hit['_id']
                results.append(fields)

        return {"total": res['hits']['total'], 'results':results}


def multifield_term_search(s_fields, start=0, pageCount=100, fields=[], es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    query = {}
    queries = []
    filter_q = None

    print "\n\n\n",s_fields,"\n\n\n"
    
    for k,v in s_fields.items():
        if "queries" in k:
            queries.extend(v)
        elif "filter" in k:
            filter_q = v
        elif "multi_match" in k:
            for item in v:
                match_query = {
                    "multi_match": {
                        "query": item[0],
                        "fields": item[1],
                        "type": "cross_fields",
                        "operator": "and"
                    }
                }
                queries.append(match_query)
        else:
            match_query = {
                "match": {
                    k: {
                        "query": v,
                        "minimum_should_match":"100%"
                    }
                }
            }
            queries.append(match_query)
        

    query["query"] =  {
            "bool": {
                "should": queries,
                "minimum_number_should_match": len(queries)
            }
        }
    query["fields"] = fields

    if filter_q is not None:
        query["filter"] = filter_q

    print "\n\n\n MULTIFIELD TERM SEARCH \n", query,"\n\n\n"
    
    res = es.search(body=query, index=es_index, doc_type=es_doc_type, from_=start, size=pageCount)
    hits = res['hits']['hits']

    results = []
    for hit in hits:
        fields = hit['fields']
        fields['id'] = hit['_id']
        results.append(fields)

    return {"total": res['hits']['total'], 'results':results}

def get_image(url, es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    if url:
        query = {
            "query": {
                "term": {
                    "url": url
                }
            },
            "fields": ["thumbnail", "thumbnail_name"]
        }
        res = es.search(body=query, index=es_index, doc_type=es_doc_type, size=500)

        hits = res['hits']['hits']
        if (len(hits) > 0):
            try:
                img = base64.b64decode(hits[0]['fields']['thumbnail'][0])
                img_name = hits[0]['fields']['thumbnail_name'][0]
                return [img_name, img]
            except KeyError:
                print "No thumbnail found"
        else:
            print "No thumbnail found"
    return [None, None]

def get_context(terms, field = "text", size=500, es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    if len(terms) > 0:
        query = {
            "query": {
                "match": {
                    field: {
                        "query": ' '.join(terms[0:]),
                        "operator" : "and"
                    }
                }
             },
            "highlight" : {
                "fields" : {
                    field: {
                        "fragment_size" : 100, "number_of_fragments" : 1
                    }
                }
            },
            "fields": ["url"]
        }

        res = es.search(body=query, index=es_index, doc_type=es_doc_type, size=size, request_timeout=600)
        hits = res['hits']

        context = {}
        for hit in hits['hits']:
            context[hit['fields']['url'][0]] = hit['highlight']['text'][0]

        return context

def range_search(field, from_val, to_val, ret_fields=[], epoch=True,  start=0, pagesCount = 200, es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es_elastic

    if epoch:
        from_val = datetime.utcfromtimestamp(long(from_val)).strftime('%Y-%m-%dT%H:%M:%S')
        to_val = datetime.utcfromtimestamp(long(to_val)).strftime('%Y-%m-%dT%H:%M:%S')

    query = {
        "query" : {
            "range" : {
                field : {
                    "gt": from_val,
                    "lte": to_val
                }
            },
        },
        "fields": ret_fields
    }

    res = es.search(body=query, index=es_index, doc_type=es_doc_type, from_=start, size=pagesCount, request_timeout=600)
    hits = res['hits']['hits']

    results = []
    for hit in hits:
        fields = hit['fields']
        fields['id'] = hit['_id']
        results.append(fields)

    return {"total": res['hits']['total'], 'results':results}

def field_missing(field, fields, pagesCount, es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    query = {
        "query" : {
            "filtered" : {
                "filter" : {
                    "missing" : { "field" : field }
                }
            }
        },
        "fields": fields
    }

    res = es.search(body=query, index=es_index, doc_type=es_doc_type, size=pagesCount, request_timeout=600)
    hits = res['hits']['hits']

    results = []
    for hit in hits:
        if hit.get('fields') != None:
            fields = hit['fields']
        else:
            fields = {}
        fields['id'] = hit['_id']
        results.append(fields)

    return results

def field_exists(field, fields, pagesCount, es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    query = {
        "query" : {
            "filtered" : {
                "filter" : {
                    "exists" : { "field" : field }
                }
            }
        },
        "fields": fields
    }

    res = es.search(body=query, index=es_index, doc_type=es_doc_type, size=pagesCount)
    hits = res['hits']['hits']

    results = []
    for hit in hits:
        fields = hit['fields']
        fields['id'] = hit['_id']
        results.append(fields)

    return results

def exec_query(query, fields, start=0, pagesCount=100, es_index='memex', es_doc_type='page', es=None):
    if es is None:
        es = default_es

    query = query
    query["fields"] = fields

    res = es.search(body=query, index=es_index, doc_type=es_doc_type, from_=start, size=pagesCount, request_timeout=30)
    hits = res['hits']['hits']

    results = []
    for hit in hits:
        fields = hit['fields']
        fields['id'] = hit['_id']
        results.append(fields)

    return {"total":res["hits"]["total"], "results":results}

if __name__ == "__main__":
    print sys.argv[1:]
    if 'string' in sys.argv[1]:
        print search(sys.argv[2], sys.argv[3:])
    elif 'term' in sys.argv[1]:
        for url in term_search(sys.argv[2], sys.argv[3:]):
            print url
    elif 'context' in sys.argv[1]:
        print get_context(sys.argv[2:])
    elif 'image' in sys.argv[1]:
        get_image(sys.argv[2])
    elif 'range' in sys.argv[1]:
        epoch = True
        if len(sys.argv) == 7:
            if 'False' in sys.argv[6]:
                epoch = False
        print range(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split(','), epoch, es_index='memex')
