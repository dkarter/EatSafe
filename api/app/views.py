from app import app
import flask
from flask import render_template
from flask import request
from flask import Response

import json
from database import session
from schema import Inspection
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.sql import func
#============================================================================
# haversine
# 
# calculates geographical distance between two locations
#
# from http://stackoverflow.com/a/4913653/2907617
#
# variables:
#   - lon1, lat1 : long/lat coordinates of first point
#   - lon2, lat2 : long/lat coordinates of second point
#   
# returns:
#   distance between them, in meters
##===========================================================================
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)

    Returns answer in m
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    m = 6367 * c * 1000
    return m

#============================================================================
# /place
# 
# look up detailed inspection information about one particular place
#
# variables:
#   - name: the name of the establishment
#   - addr: the address of the establishment
#
# returns:
#   json string object that contains a list of previous inspections
##===========================================================================
@app.route('/place')
def place():
    name = request.args.get('name', '', type=str)
    address = request.args.get('addr', '', type=str)
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
# zipped, ii contains
# [[date1, date2, date3, ...],
#  [result1, result2, result3, ...],
#  [violation1, violation2, violation3, ...],
#  [itype1, itype2, itype3, ...]]
##===========================================================================
    ii = zip(*inspection_info)
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

        if d < max_dist:
            results.append({
                    'name': name,
                    'address': address,
                    'dist': miles,
                    'score': int(score),
                    'count': count
                })
    
    sorted_results = sorted(results, key=lambda k: k['dist'])[:20]
    
    # formulate json response
    return Response(json.dumps(sorted_results), mimetype='text/json')
