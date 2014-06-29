from app import app
import flask
from flask import render_template
from flask import request
import json
from database import session
from schema import Inspection
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.sql import func

def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)

    Returns answer in km
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
# look up detailed inspection information about one particular place
##===========================================================================
@app.route('/place'):
    name = request.args.get('name', '', type=str)
    address = request.args.get('addr', '', type=str)
    inspection_info = session.query(
            Inspection.Risk,
            Inspection.Inspection_Date,
            Inspection.Results,
            Inspection.Violations,
            Inspection.Inspection_Type).filter(
                    Inspection.AKA_Name==name and
                    Inspection.Address==address).all()
    

#============================================================================
# find nearby restaurants and their aggregate health inspection scores
##===========================================================================
@app.route('/near')
def check():

    longitude = request.args.get('long', '', type=float)
    latitude = request.args.get('lat', '', type=float)
    
    # default max_dist: 500
    max_dist = request.args.get('d', '', type=float) 

    # todo: return error
    assert longitude and latitude
        

#============================================================================
# get all unique restaurants from the database
##===========================================================================

    all_restaurants = \
            session.query(Inspection.AKA_Name,
                    Inspection.Address,
                    Inspection.Longitude,
                    Inspection.Latitude,
                    func.avg(Inspection.Results),
                    func.count(Inspection.Results)).group_by(Inspection.AKA_Name,
                                                Inspection.Address).all()

#============================================================================
# loop through all restaurants, calculate distance
##===========================================================================
    
    results = []

    for name, address, store_long, store_lat, score, count in all_restaurants:
        if not store_long or not store_lat:
            continue
        d = haversine(longitude, 
                latitude, 
                store_long, 
                store_lat)
        
        if d < max_dist:
            results.append({
                    'name': name,
                    'address': address,
                    'dist': d,
                    'score': int(score),
                    'count': count
                })
    
    sorted_results = sorted(results, key=lambda k: k['dist'])[:20]
#============================================================================
# formulate json response
##===========================================================================
    return json.dumps(sorted_results)
"""
#============================================================================
# get detailed inspection information on the results
##===========================================================================
    final = []
    for restaurant in sorted_results:
        inspection_info = session.query(
                Inspection.Risk,
                Inspection.Inspection_Date,
                Inspection.Results,
                Inspection.Violations,
                Inspection.Inspection_Type).filter(
                        Inspection.AKA_Name==restaurant['name'] and
                        Inspection.Address==restaurant['address']).all()

        ii = zip(*inspection_info)
        
        # if the latest inspection showed they went out of business, pass
        if ii[2][-1] == 'Out of Business':
            continue

#============================================================================
# Calculate "safety score" = # Passed Inspections / # Failed Inspections
##===========================================================================
        sum_score = 0
        count = 0
        for result in ii[2]:
            if result == 'Pass':
                sum_score += 100
            elif result == 'Pass w/ Conditions':
                sum_score += 50
            else:
                # result is either "Out of Business" or "Fail"
                pass

            count += 1

        safety_score = sum_score/count
        restaurant['score'] = safety_score
        restaurant['count'] = count
        final.append(restaurant)
        
"""
