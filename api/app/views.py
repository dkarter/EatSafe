from app import app
import flask
from flask import render_template
from flask import request
from flask import Response
from flask import abort

from simplejson import JSONDecodeError

import json
from database import session
from schema import Inspection, Restaurant
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.sql import func
from helpers import haversine, get_rating, get_geo, get_yelp_json
import requests
import urllib
from settings import gkey, ykey

#google API query
gquery="https://maps.googleapis.com/maps/api/place/textsearch/json?query={q}&key=" + gkey
#yelp API query
yquery = 'http://api.yelp.com/business_review_search?term={name}&location={addr}&limit=1&ywsid=' + ykey
#google instant API
ginstant = 'https://maps.googleapis.com/maps/api/place/autocomplete/json?input={substring}&types=establishment&radius=50000&key=' + gkey


#============================================================================
# Failed attempt at creating a web version of the app
##===========================================================================
@app.route('/map')
def show_map():
    return render_template('map.html', key=gkey)

#============================================================================
# /instant
# Google Places Autocomplete API endpoint
# Arguments: query -- query
#            long  -- longitude
#            lat   -- latitude 
#       
#   if long and lat are not provided, the center of Chicago is used
#   
#   returns a JSON object that contains a list of matches, where each match is
#   {
#       'name': <name of institution>,
#       'place_id': <Google Place ID of institution>
#   }
##===========================================================================
@app.route('/instant')
def instant():
    query = request.args.get('query', '', type=str)
    gq = ginstant.format(substring=urllib.quote_plus(query))
    
    longitude = request.args.get('long', '-87.625916', type=str)
    latitude = request.args.get('lat', '41.903196', type=str)

    gq += '&location={lat},{lng}'.format(lat=latitude,
            lng=longitude)
    
    try:
        r = requests.get(gq)
    except requests.ConnectionError:
        print "ConnectionError in Google Instant API--check connection?"
        return Response(json.dumps({}), mimetype='text/json')

    if not r.ok:
        print "Request to Google Instant API failed: {}.".format(r.code)
        return Response(json.dumps({}), mimetype='text/json')
    
    try:
        j = r.json()
    except JSONDecodeError:
        print "JSONDecodeError in instant search:", r.text
        return Response(json.dumps({}), mimetype='text/json')
    
    result = []
    if j and j.has_key('predictions'):
        for pred in j['predictions'][:4]:
            item = {'name': pred['description'],
                    'place_id': pred['id']}

            result.append(item)
        
    return Response(json.dumps(result), mimetype='text/json')


#============================================================================
# /place
# 
# look up detailed inspection information about one particular place
#
# variables:
# accepts either
#   - name: the name of the establishment
#   - addr: the address of the establishment
#
# OR
#
#   - query: a single query that mashes name and addr together
#
# if both are provided, name+addr takes precedence
#
# returns:
#   json object that contains summary information about the restaurant
#       as well as a list of previous inspections
#   
#   
##===========================================================================
@app.route('/place')
def place():
    query = request.args.get('query', '', type=str)
    longitude = request.args.get('long', '', type=str)
    latitude = request.args.get('latitude', '', type=str)
    simple = request.args.get('simple', False, type=bool)

    json_tuple= get_yelp_json(query, longitude, latitude)
    if json_tuple:
        gjs, yjs = json_tuple
    else:
        return Response(json.dumps({

            }), mimetype='text/json')

################# FIX THIS:
    restaurant_info = session.query(
            Restaurant.db_name,
            Restaurant.db_addr,
            Restaurant.rating_img_url,
            Restaurant.review_count,
            Restaurant.yelp_name,
            Restaurant.yelp_address,
            Restaurant.zip_code,
            Restaurant.photo_url).filter(Restaurant.yelp_id==yjs['id']).all()
    
    if not restaurant_info:
        return Response(json.dumps({
            'name': gjs['name'],
            'address': yjs['address1'],
            'pic': yjs['photo_url'],
            'yelp_rating_pic': yjs['rating_img_url'],
            'yelp_review_count': yjs['review_count']
            }), mimetype='text/json')
    else:
        ri = restaurant_info[0]

    db_name = ri[0]
    db_addr = ri[1]

    general_stats = \
            session.query(Inspection.AKA_Name,
                    Inspection.Address,
                    Inspection.Longitude,
                    Inspection.Latitude,
                    func.avg(Inspection.Results),
                    func.count(Inspection.Results),
                    func.count(Inspection.Complaint)).group_by(Inspection.AKA_Name,
                                                Inspection.Address).\
                    filter(db_name==Inspection.AKA_Name,
                            db_addr==Inspection.Address).all()


    returned = {
            'yelp_rating_pic': ri[2],
            'yelp_review_count': ri[3],
            'name': ri[4],
            'address': ri[5].strip(),
            'address2': 'Chicago, IL, ' + ri[6].strip(), 
            'pic': ri[7]
            }
            
    inspection_info = session.query(
            Inspection.Inspection_Date,
            Inspection.Results,
            Inspection.Violations,
            Inspection.Inspection_Type,
            Inspection.Longitude,
            Inspection.Latitude).filter(
                    Inspection.AKA_Name==db_name and
                    Inspection.Address==db_addr).all()
        
#============================================================================
# zipped, ii contains
# [[date1, date2, date3, ...],
#  [result1, result2, result3, ...],
#  [violation1, violation2, violation3, ...],
#  [itype1, itype2, itype3, ...]]
##===========================================================================
    ii = zip(*inspection_info)
    score = sum(ii[1])/len(ii[1])
    rating = get_rating(score)
    
    # count number of failures
    failures = 0
    for n in ii[1]:
        if n == 0:
            failures += 1

    # count number of complaints
    complaints = 0
    for n in ii[3]:
        if n == 'Complaint':
            failures += 1
    
    returned['otr_reserve_url'] = ''
    if not simple:
        details = []
        for inspection in inspection_info:
            details.append({
                    'date': inspection[0],
                    'result': inspection[1],
                    #'violations': inspection[2],
                    'itype': inspection[3]
                    })
        
        returned['details'] = details
    try:
        otr = requests.get('http://opentable.herokuapp.com/api/restaurants?name={name}&\
                address={addr}&city=Chicago&zip={zip_code}'.format(
                    name=returned['name'],
                    addr=returned['address'],
                    zip_code=ri[6]))
    except requests.ConnectionError:
        pass

    if otr and otr.ok:
        otrj = otr.json()
        if otrj['total_entries'] > 0:
            otrid = otrj['restaurants'][0]
            try:
                otr_reserve_url = otrj['restaurants'][0]['mobile_reserve_url']
            except IndexError:
                pass
    
            returned['otr_reserve_url'] = otr_reserve_url
    
    returned['complaints'] = complaints
    returned['score'] = score
    returned['rating'] = rating
    returned['count'] = len(ii[1])
    returned['failures'] = failures
    
    return Response(json.dumps(returned), mimetype='text/json')


@app.route('/near')
def check():
    """

    check():

     route /near?

     find nearby restaurants and their aggregate health inspection scores
     
     required variables:
     -long: the longitude to search near
     -lat: the latitude to search near

     returns:
     {
     'name': name of the restaurant,
     'address': address,
     'google_id': google place ID--> use for if they click
     'dist': distance in miles,
     'pic': link to photo,
     'rating': letter rating (A, B, C, F, ?),
     'yelp_rating': yelp rating (float: 0, 0.5, ..., 3.5, 4)
     }
     
     a json string object of list of closest 20 restaurants and their health
     inspection scores
     
     note: distance is returned in miles

    """
    MAX_DIST = 5000
    longitude = request.args.get('long', '', type=float)
    latitude = request.args.get('lat', '', type=float)

    if not (longitude and latitude):
        abort(400)

    # get all unique restaurants from the database

    all_restaurants = session.query(
        Restaurant.google_id,
        Restaurant.db_name,
        Restaurant.db_addr,
        Restaurant.google_name,
        Restaurant.google_lat,
        Restaurant.google_lng,
        Restaurant.yelp_name,
        Restaurant.yelp_rating,
        Restaurant.yelp_review_count,
        Restaurant.yelp_photo_url,
        Restaurant.yelp_rating_img_url,
        Restaurant.yelp_address,
        Restaurant.yelp_zip,
        Restaurant.yelp_phone,
        Restaurant.rating,
        Restaurant.complaints,
        Restaurant.db_long,
        Restaurant.db_lat,
        Restaurant.num).all()

    key = {'complaints': 15,
     'db_addr': 2,
     'db_name': 1,
     'google_id': 0,
     'google_lat': 4,
     'google_lng': 5,
     'google_name': 3,
     'rating': 14,
     'yelp_address': 11,
     'yelp_name': 6,
     'yelp_phone': 13,
     'yelp_photo_url': 9,
     'yelp_rating': 7,
     'yelp_rating_img_url': 10,
     'yelp_review_count': 8,
     'db_long':16,
     'db_lat':17,
     'count': 18}

    # loop through all restaurants, calculate distance
    valid = []
    results = []

    for row in all_restaurants:

        # throw away all restaurants without google IDs
        if not row[key['google_id']]:
            continue
        
        # throw away restaurants without longitude
        if not row[key['db_long']] and not row[key['google_lng']]:
            continue
        
        # use google stuff when we have it
        if row[key['google_lng']]:
            lng, lat = map(float, 
                    (row[key['google_lng']], row[key['google_lat']]))
        else:
            lng, lat = row[key['db_long']], row[key['db_lat']]

        d = haversine(longitude, latitude, lng, lat)

        if d < MAX_DIST:
            valid.append({row: d})

    closest = sorted(valid, key=lambda x: x.get)[:20]
    
    for row in closest:
        row,d = row.items()[0]
        if row[key['yelp_address']]:
            addr = row[key['yelp_address']]
        else:
            addr = row[key['db_addr']]

        if row[key['yelp_photo_url']]:
            photo = row[key['yelp_photo_url']]
        else:
            photo = 'http://s3-media1.fl.yelpcdn.com/assets/2/www/img/5f69f303f17c/default_avatars/business_medium_square.png'
        
        rating = get_rating(row[key['rating']])
        if rating == 'A' and row[key['count']] <= 1:
            rating = '-'
        
        if d < 1609:
            miles = '%.2f'%(d*0.000621371)
        else:
            miles = '%.1f'%(d*0.000621371)

        results.append({
                'name': row[key['google_name']],
                'id': row[key['google_id']],
                'address': addr,
                'dist': miles,
                'pic': photo,
                'rating': rating,
                'yelp_rating': row[key['yelp_rating']]
            })
    

    # formulate json response
    return Response(json.dumps(results), mimetype='text/json')

@app.errorhandler(400)
def bad_request():
    return json.dumps({'code': 'bad API arguments'})
