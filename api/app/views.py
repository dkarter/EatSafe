from app import app
import flask
from flask import render_template
from flask import request
from flask import Response
from simplejson import JSONDecodeError

import json
from database import session
from schema import Inspection, Yelp
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
        for pred in j['predictions'][:8]:
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

    gjs, yjs = get_yelp_json(query, longitude, latitude)
    
    if not yjs['id']:
        return Response(json.dumps({

            
            }), mimetype='text/json')

    restaurant_info = session.query(
            Yelp.db_name,
            Yelp.db_addr,
            Yelp.rating_img_url,
            Yelp.review_count,
            Yelp.yelp_name,
            Yelp.yelp_address,
            Yelp.zip_code,
            Yelp.photo_url).filter(Yelp.yelp_id==yjs['id']).all()
    
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
    
    returned['score'] = score
    returned['rating'] = rating
    returned['count'] = len(ii[1])

    if not simple:
        details = []
        for inspection in inspection_info:
            details.append({
                    'date': inspection[0],
                    'result': inspection[1],
                    'violations': inspection[2],
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
                otr_reserve_url = ''
    
            returned['otr_reserve_url'] = otr_reserve_url

    
    return Response(json.dumps(returned), mimetype='text/json')

    """
    if name and address:
        inspection_info = session.query(
                Inspection.Inspection_Date,
                Inspection.Results,
                Inspection.Violations,
                Inspection.Inspection_Type).filter(
                        Inspection.AKA_Name==name and
                        Inspection.Address==address).all()
        
        result = []
        for inspection in inspection_info:
            result.append({
                    'date': inspection[0],
                    'result': inspection[1],
                    'violations': inspection[2],
                    'itype': inspection[3]
                    })
        return Response(json.dumps(result), mimetype='text/json')
        """

#============================================================================
# /near
#
# find nearby restaurants and their aggregate health inspection scores
# 
# variables:
# -long: the longitude to search near
# -lat: the latitude to search near
# -d: the radius to search around (in meters)
#
# returns:
# a json string object of list of closest 20 restaurants and their health
# inspection scores
# 
# note: distance is returned in miles
#
##===========================================================================
@app.route('/near')
def check():

    longitude = request.args.get('long', '', type=float)
    latitude = request.args.get('lat', '', type=float)

    if not (longitude and latitude):
        query = request.args.get('query', '', type=str)
        geo = get_geo(query)
        longitude = geo['long']
        latitude = geo['lat']
        max_dist = 500

        print longitude, latitude

    
    max_dist = request.args.get('d', '', type=float) 

    # todo: return error
    assert longitude and latitude and max_dist
        

    # get all unique restaurants from the database

    all_restaurants = \
            session.query(Inspection.AKA_Name,
                    Inspection.Address,
                    Inspection.Longitude,
                    Inspection.Latitude,
                    func.avg(Inspection.Results),
                    func.count(Inspection.Results)).group_by(Inspection.AKA_Name,
                                                Inspection.Address).all()

    # loop through all restaurants, calculate distance
    
    results = []

    for name, address, store_long, store_lat, score, count in all_restaurants:
        if not store_long or not store_lat:
            continue
        d = haversine(longitude, 
                latitude, 
                store_long, 
                store_lat)
        
        if d < 1609:
            miles = '%.2f'%(d*0.000621371)
        else:
            miles = '%.0f'%(d*0.000621371)
        
        rating = get_rating(score)

        if d < max_dist:
            restaurant_info = session.query(
                    Yelp.yelp_name,
                    Yelp.yelp_id,
                    Yelp.rating_img_url,
                    Yelp.review_count,
                    Yelp.yelp_address,
                    Yelp.zip_code,
                    Yelp.photo_url).filter(
                            Yelp.db_name==name, 
                            Yelp.db_addr==address).all()
            if restaurant_info:
                ri = restaurant_info[0]
                use_name = ri[0]
                rating_pic = ri[2]
                review_count = ri[3]
                use_address = ri[4] + ', ' + ri[5]
                photo = ri[6]
            else:
                use_name = name
                rating_pic = ''
                review_count = 0
                use_address = address
                photo = 'http://s3-media1.fl.yelpcdn.com/assets/2/www/img/5f69f303f17c/default_avatars/business_medium_square.png'
            results.append({
                    'name': use_name,
                    'address': use_address,
                    'dist': miles,
                    'score': int(score),
                    'count': count,
                    'pic': photo,
                    'rating': rating,
                    'yelp_rating_pic': rating_pic
                })
    
    sorted_results = sorted(results, key=lambda k: k['dist'])[:20]
    
    # formulate json response
    return Response(json.dumps(sorted_results), mimetype='text/json')
