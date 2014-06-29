from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, Date

Base = declarative_base()

class Inspection(Base):
    __tablename__ = 'food_inspections'
    Inspection_ID = Column(String, primary_key=True)
    DBA_Name = Column(String)
    AKA_Name = Column(String)
    License_No = Column(Integer)
    Facility_Type = Column(String)
    Risk = Column(String)
    Address = Column(String)
    City = Column(String)
    State = Column(String)
    Zip = Column(Integer)
    Inspection_Date = Column(String)
    Inspection_Type = Column(String)
    Results = Column(String)
    Violations = Column(String)
    Latitude = Column(Float)
    Longitude = Column(Float)

class Yelp(Base):
    __tablename__ = 'yelp'
    yelp_id = Column(String, primary_key=True)
    db_name = Column(String)
    db_addr = Column(String)
    yelp_name = Column(String)
    avg_rating = Column(Float)
    review_count = Column(Integer)
    photo_url = Column(String)
    rating_img_url = Column(String)
    yelp_address = Column(String)
    zip_code = Column(String)
    phone = Column(String)
