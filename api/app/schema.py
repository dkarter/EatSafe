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
#    Inspection_Date = Column(Date)
    Inspection_Date = Column(String)
    Inspection_Type = Column(String)
    Results = Column(String)
    Violations = Column(String)
    Latitude = Column(Float)
    Longitude = Column(Float)

