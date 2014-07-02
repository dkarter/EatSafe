import requests
import csv
import cPickle as p
import pandas as pd
import urllib
import sys

sys.path.append('api/app')
from settings import ykey, gkey

yquery = 'http://api.yelp.com/business_review_search?\
term={name}\
&lat={lat}\
&long={lng}\
&radius=.3\
&ywsid={y}\
&limit=1'

yquery_no_geo = 'http://api.yelp.com/business_review_search?\
term={name}\
&location={addr}\
&radius=.3\
&ywsid={y}\
&limit=1'

gquery = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?\
keyword={q}\
&location={lat},{lng}\
&radius=1000\
&key={g}'

gquery_no_geo = 'https://maps.googleapis.com/maps/api/place/textsearch/json?\
query={q}\
&key={g}'

errors = ''
yelp_fail = 0
google_fail = 0
results = []

def dump_output():
    global results, errors

    df = pd.DataFrame(results)
    with open('scraped-all.p', 'w') as out:
        p.dump(df, out)

    with open('scrape-errors.txt', 'w') as out:
        out.write(errors)

def get_with_error_handling(q, site):
    global errors, google_fail, yelp_fail

    try:
        r = requests.get(q)

    except requests.ConnectionError:

        print "Connection error on Yelp try %i with %s, %s"%(i, name, addr)
        errors += "Connection error on Yelp try %i with %s, %s\n"%(i, name, addr)
        return {}
    
    if not r.ok:

        print "Bad response on Yelp try %i with %s, %s"%(i, name, addr)
        errors += "Bad response on Yelp try %i with %s, %s\n"%(i, name, addr)

        return {}

    try:

        if site == 'Yelp':
            j = r.json()['businesses'][0]
        elif site == 'Google':
            j = r.json()['results'][0]

    except IndexError:

        if site == 'Yelp':
            yelp_fail += 1

            js = r.json()

            if js['message']['code'] == '4':

                print "Yelp daily limit exceeded!! Try %i with %s, %s: %s"%(i, name, addr, js['message']['text'])
                errors += "Yelp error try %i with %s, %s: %s\n"%(i, name, addr, js['message']['text'])
                return {'quit': True}

        elif site == 'Google':
            google_fail += 1

            errors += "Empty response on Google try %i with %s, %s\n"%(i, name, addr)

        return {}
    
    return j

def skip_ahead(n, reader):
    i = 0
    for _ in reader:
        i+= 1
        if i > n:
            break

with open('data/unique_restaurants_geo.csv', 'r') as f:

    dialect = csv.Sniffer().sniff(f.read(1024))
    f.seek(0)
    reader = csv.reader(f, dialect)
    i=0
    #skip_ahead
    print "Starting scrape on i={}".format(i)

    for name, addr, latitude, longitude in reader:
        
        i+= 1

        if latitude and longitude:

            yq = yquery.format(
                    name=urllib.quote_plus(name),
                    addr=urllib.quote_plus(addr),
                    lat=latitude,
                    lng=longitude,
                    y=ykey)
            gq = gquery.format(
                    q=urllib.quote_plus(name) + ', ' + urllib.quote_plus(addr),
                    addr=urllib.quote_plus(addr),
                    lat=latitude,
                    lng=longitude,
                    g=gkey)

        else:

            yq = yquery_no_geo.format(
                    name=urllib.quote_plus(name),
                    addr=urllib.quote_plus(addr),
                    y=ykey)
            gq = gquery_no_geo.format(
                    q=urllib.quote_plus(name) + ', ' + urllib.quote_plus(addr),
                    addr=urllib.quote_plus(addr),
                    g=gkey)

        want = {}
        want['db_name'] = name
        want['db_addr'] = addr
        jg = get_with_error_handling(gq, site='Google')
        
        want['google_id'] = jg.get('place_id', '')
        want['google_name'] = jg.get('name', '')
        want['google_vicinity'] = jg.get('vicinity', '')
        want['google_rating'] = jg.get('rating', '')
        want['google_price'] = jg.get('price_level', '')
        want['google_lat'] = jg.get('geometry', {}).get('location', {}).get('lat', '')
        want['google_lng'] = jg.get('geometry', {}).get('location', {}).get('lng', '')

        if want['google_lat']:

            yq = yquery.format(
                    name=urllib.quote_plus(name),
                    addr=urllib.quote_plus(addr),
                    lat=want['google_lat'],
                    lng=want['google_lng'],
                    y=ykey)

        
        jy = get_with_error_handling(yq, site='Yelp')
        
        if jy.has_key('quit'):
            print 'wrapping up and quitting...'
            break
        else:
            want['yelp_name'] = jy.get('name', '')
            want['yelp_rating'] = jy.get('avg_rating', '')
            want['yelp_review_count'] = jy.get('review_count', '')
            want['yelp_photo_url'] = jy.get('photo_url', '')
            want['yelp_rating_img_url'] = jy.get('rating_img_url', '')
            want['yelp_address'] = jy.get('address1', '')
            want['yelp_zip'] = jy.get('zip', '')
            want['yelp_phone'] = jy.get('phone', '')
            want['yelp_id'] = jy.get('id', '')

            results.append(want)
            
            if i < 10:
                print i, want, google_fail, yelp_fail
            if i%300 == 0:
                print i, want, google_fail, yelp_fail

dump_output()

