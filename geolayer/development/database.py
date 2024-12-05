"""
Utility: database functions
"""
# Author(s): Davide.De-Marchi@ec.europa.eu
# Copyright © European Union 2024
# 
# Licensed under the EUPL, Version 1.2 or as soon they will be approved by 
# the European Commission subsequent versions of the EUPL (the "Licence");
# 
# You may not use this work except in compliance with the Licence.
# 
# You may obtain a copy of the Licence at:
# https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

# Unless required by applicable law or agreed to in writing, software
# distributed under the Licence is distributed on an "AS IS"
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied.
# 
# See the Licence for the specific language governing permissions and
# limitations under the Licence.

# Python import
import psycopg2
from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import pandas as pd
import geopandas as gpd

# Vois imports
from vois.vuetify import dialogGeneric


#####################################################################################################################################################
# database class
# ####################################################################################################################################################
class database():
    
    # Initialize
    def __init__(self, outputservice=None):
        
        self.outputservice = outputservice
        
        # Read database.ini file
        self.config = self.readConfigFile()
        
        # List of column names of the last execute sql command
        self.column_names = []
        
        
        
    # Return an sqlalchemy  engine
    def engine(self, dbschema='public'):
        engine = None
        try:
            db_connection_url = "postgresql://%s:%s@%s:%d/%s"%(self.config['user'], self.config['password'], self.config['host'], int(self.config['port']), self.config['database'])
            engine = create_engine(db_connection_url, poolclass=NullPool, connect_args={'options': '-csearch_path={}'.format(dbschema)})
        except (Exception, psycopg2.errors.ProgrammingError) as error:
            #print(error)
            dialogGeneric.dialogGeneric(title='DB Error!',
                                        text=str(error), dark=True,
                                        show=True, addclosebuttons=True, width=800,
                                        fullscreen=False, content=[], output=self.outputservice)
        return engine
    
    
    # Return a pandas DataFrame (using SQLAlchemy connection)
    def dataframe(self, sqlcommand, dbschema='public'):
        df = None
        try:
            db_connection_url = "postgresql://%s:%s@%s:%d/%s"%(self.config['user'], self.config['password'], self.config['host'], int(self.config['port']), self.config['database'])
            engine = create_engine(db_connection_url, poolclass=NullPool, connect_args={'options': '-csearch_path={}'.format(dbschema)})
            df = pd.read_sql_query(sqlcommand, con=engine)
        except (Exception, psycopg2.errors.ProgrammingError) as error:
            #print(error)
            dialogGeneric.dialogGeneric(title='DB Error!',
                                        text=str(error), dark=True,
                                        show=True, addclosebuttons=True, width=800,
                                        fullscreen=False, content=[], output=self.outputservice)
        finally:
            engine.dispose()
        return df

    
    # Return a geopandas GeoDataFrame (using SQLAlchemy connection)
    def geodataframe(self, sqlcommand, dbschema='public', geom_col='geom'):
        df = None
        try:
            db_connection_url = "postgresql://%s:%s@%s:%d/%s"%(self.config['user'], self.config['password'], self.config['host'], int(self.config['port']), self.config['database'])
            engine = create_engine(db_connection_url, poolclass=NullPool, connect_args={'options': '-csearch_path={}'.format(dbschema)})
            df = gpd.read_postgis(sqlcommand, con=engine, geom_col=geom_col)
        except (Exception, psycopg2.errors.ProgrammingError) as error:
            #print(error)
            dialogGeneric.dialogGeneric(title='DB Error!',
                                        text=str(error), dark=True,
                                        show=True, addclosebuttons=True, width=800,
                                        fullscreen=False, content=[], output=self.outputservice)
        finally:
            engine.dispose()
        return df
    
        
    # Run SQL query: returns records as a list of tuples (using psycopg2) N.B. Probably superseeded by self.dataframe!!!
    def query(self, sqlcommand):
        conn = None
        self.column_names = []
        records = []
        try:
            conn = psycopg2.connect(**self.config)

            cur = conn.cursor()

            cur.execute(sqlcommand)
            
            self.column_names = [desc[0] for desc in cur.description]

            records = cur.fetchall()

            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            #print(error)
            dialogGeneric.dialogGeneric(title='DB Error!',
                                        text=str(error), dark=True,
                                        show=True, addclosebuttons=True, width=800,
                                        fullscreen=False, content=[], output=self.outputservice)
        finally:
            if conn is not None:
                conn.close()
            return records
        

    # Execute of an SQLcommand: returns bool
    def execute(self, sqlcommand, showError=True):
        conn = None
        self.column_names = []
        res = False
        try:
            conn = psycopg2.connect(**self.config)

            cur = conn.cursor()

            cur.execute(sqlcommand)
            
            conn.commit()
            
            cur.close()
            
            res = True
        except (Exception, psycopg2.DatabaseError) as error:
            #print(error)
            if showError:
                dialogGeneric.dialogGeneric(title='DB Error!',
                                            text=str(error), dark=True,
                                            show=True, addclosebuttons=True, width=800,
                                            fullscreen=False, content=[], output=self.outputservice)
        finally:
            if conn is not None:
                conn.close()
            return res

        
    # Read the configuration file for database access
    def readConfigFile(self, filename='database.ini', section='postgresql'):
        parser = ConfigParser()
        parser.read(filename)

        db = {}
        if parser.has_section(section):
            params = parser.items(section)
            for param in params:
                db[param[0]] = param[1]
        else:
            raise Exception('Section {0} not found in the {1} file'.format(section, filename))

        return db
