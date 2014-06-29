import requests
import csv
import cPickle as p
import pandas as pd
import urllib

query = 'http://api.yelp.com/business_review_search?term={name}&location={addr}+Chicago+IL&ywsid=***REMOVED***&limit=1'

with open('data/name_addr.csv', 'r') as f:
    dialect = csv.Sniffer().sniff(f.read(1024))
    f.seek(0)
    reader = csv.reader(f, dialect)   
    i = 0
    for _ in reader:
        i+= 1
        if i == 1803:
            break
        continue

    print "Starting scrape on i={}".format(i)
    results = []
    for name, addr in reader:
        i+= 1
        try:
            r = requests.get(query.format(
                name=urllib.quote_plus(name), 
                addr=urllib.quote_plus(addr)))
        except requests.ConnectionError:
            print "Connection error on try %i with %s, %s"%(i, name, addr)
            continue

        
        if not r.ok:
            print "Bad response on try %i with %s, %s"%(i, name, addr)
            continue

        try:
            j = r.json()['businesses'][0]
        except IndexError:
            continue
        
        want = {}
        want['db_name'] = name
        want['db_addr'] = addr
        want['yelp_name'] = j['name']
        want['avg_rating'] = j['avg_rating']
        want['review_count'] = j['review_count']
        want['photo_url'] = j['photo_url']
        want['rating_img_url'] = j['rating_img_url']
        want['yelp_address'] = j['address1']
        want['zip'] = j['zip']
        want['phone'] = j['phone']
        want['yelp_id'] = j['id']

        results.append(want)
        
        if i%300 == 0:
            print i, want

        if i == 9980:
            break

df = pd.DataFrame(results)
with open('scraped177-.p', 'w') as out:
    p.dump(df, out)
