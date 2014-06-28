# coding: utf-8
#============================================================================
# (Run interactively) 
# Exploration of the Food Inspection dataset for Battlehacks 2014
# Sam Zhang
# Dorian Karter
##===========================================================================
import pandas as pd
df = pd.read_csv('Food_Inspections.csv')
df.head()
df.shape
df.tail()
df['Risk'].value_counts()
df['DBA Name'].value_counts().shape
df['AKA Name'].value_counts().shape
df['Inspection ID'].value_counts().shape
df['Results'].value_counts()
