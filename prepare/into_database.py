#============================================================================
# Imports Chicago Food Inspection data into a database
##===========================================================================

import pandas as pd
import sqlite3 as db

def recode(result):
    if result == 'Pass':
        return 100
    elif result == 'Pass w/ Conditions':
        return 90
    else:
        return 0

df = pd.read_csv('data/Food_Inspections.csv')
df['Inspection Date'] = df['Inspection Date'].apply(
        lambda x: x.replace('/', '-'))

df['Bankrupt'] = df['Results'] == 'Out of Business'
df['Complaint'] = df['Results'] == 'Complaint'
df['Failure'] = df['Results'] == 'Fail'

df['Results'] = df['Results'].apply(recode)

with db.connect('db/food_inspections.db', 
        detect_types=db.PARSE_DECLTYPES) as con:
    df.to_sql(con=con, name='food_inspections',
            if_exists='replace',
            flavor='sqlite')
