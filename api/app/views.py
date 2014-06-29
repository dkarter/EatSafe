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
from helpers import haversine, get_rating, get_geo, get_yelp_id
import requests
import urllib

from settings import gkey, ykey

#google API query
gquery="https://maps.googleapis.com/maps/api/place/textsearch/json?query={q}&key=" + gkey
#yelp API query
yquery = 'http://api.yelp.com/business_review_search?term={name}&location={addr}&limit=1&ywsid=' + ykey
#google instant API
ginstant = 'https://maps.googleapis.com/maps/api/place/autocomplete/json?input={substring}&types=establishmen&radius=500&key=' + gkey

@app.route('/instant')
def instant():
    query = request.args.get('query', '', type=str)
    ginstant.format({query:urllib.quote_plus(query)})

    longitude = request.args.get('long', '', type=str)
    latitude = request.args.get('lat', '', type=str)

    if longitude and latitude:
        query += 'loc={lat},{lng}'.format({
                lat:latitude,
                lng:longitude})


    return Request(json.dumps(result, mimetype='text/json'))


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
#   json string object that contains a list of previous inspections
##===========================================================================
@app.route('/place')
def place():
    query = request.args.get('query', '', type=str)
    longitude = request.args.get('long', '', type=str)
    latitude = request.args.get('latitude', '', type=str)
    yelp_id = get_yelp_id(query, longitude, latitude)
    
    if not yelp_id:
        return Response(json.dumps({}), mimetype='text/json')

    restaurant_info = session.query(
            Yelp.db_name,
            Yelp.db_addr,
            Yelp.rating_img_url,
            Yelp.review_count,
            Yelp.yelp_name,
            Yelp.yelp_address,
            Yelp.zip_code,
            Yelp.photo_url).filter(Yelp.yelp_id==yelp_id).all()

    if not restaurant_info:
        return Response(json.dumps({}), mimetype='text/json')
    else:
        ri = restaurant_info[0]

    db_name = ri[0]
    db_addr = ri[1]

    returned = {
            'yelp_rating_pic': ri[2],
            'yelp_review_count': ri[3],
            'name': ri[4],
            'addr': ri[5].strip() +\
                    ' ' +\
                    ri[6].strip(),
            'pic': ri[7]
            }
            
    inspection_info = session.query(
            Inspection.Inspection_Date,
            Inspection.Results,
            Inspection.Violations,
            Inspection.Inspection_Type).filter(
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

    details = []
    for inspection in inspection_info:
        details.append({
                'date': inspection[0],
                'result': inspection[1],
                'violations': inspection[2],
                'itype': inspection[3]
                })
    
    returned['details'] = details
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
                photo = 'http://placekitten.com/100/100'
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
