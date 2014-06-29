from os.path import dirname, join

DATABASE_DIR = '/home/sam/battlehack/EatSafe/db/food_inspections.db'
#PROJECT_DIR = dirname(__file__)

DATABASES = {
        'PREFIX': 'sqlite:////',
        'NAME': DATABASE_DIR
        #'NAME': join(PROJECT_DIR, 'cygnet.db')
        }
