from pymongo import MongoClient
import pandas as pd
import json
from urllib.parse import quote_plus
import os

# Get MongoDB URI from environment variable, fallback to localhost if not set
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/capstone')

class Database:
    def __init__(self):
        print("MONGO_URI:", MONGO_URI, flush=True)
        # For Atlas, force TLS and ignore cert verification
        if 'mongodb+srv://' in MONGO_URI:
            self.client = MongoClient(MONGO_URI + "&tls=true")
        else:
            self.client = MongoClient(MONGO_URI)
            
        self.db = self.client.capstone
        self.zip_data = self.db.zip_data
        self.state_lookup = self.db.state_lookup

    def initialize_collections(self, zip_data_df, state_lookup_dict):
        """Initialize collections with data"""
        # Convert ZIP codes to string with leading zeros
        zip_data_df['zip_code'] = zip_data_df['zip_code'].astype(str).str.zfill(5)
        
        # Convert DataFrame to list of dictionaries
        zip_records = zip_data_df.to_dict('records')
        
        # Clear existing data and insert new data
        self.zip_data.delete_many({})
        self.zip_data.insert_many(zip_records)
        
        # Create index on zip_code for faster lookups
        self.zip_data.create_index('zip_code')
        
        # Clear existing state lookup data
        self.state_lookup.delete_many({})
        
        # Insert state lookup data
        state_lookup_records = []
        for state, data in state_lookup_dict.items():
            state_lookup_records.append({
                'state': state,
                'data': data
            })
        self.state_lookup.insert_many(state_lookup_records)
        
        # Create index on state for faster lookups
        self.state_lookup.create_index('state')

    def get_zip_data(self):
        """Get all ZIP data as a DataFrame"""
        cursor = self.zip_data.find({}, {'_id': 0})
        return pd.DataFrame(list(cursor))

    def get_state_data(self, state_code):
        """Get data for a specific state"""
        state_doc = self.state_lookup.find_one({'state': state_code})
        if state_doc:
            return pd.DataFrame(state_doc['data'])
        return pd.DataFrame()

    def get_zip_info(self, zip_code):
        """Get information for a specific ZIP code"""
        return self.zip_data.find_one({'zip_code': zip_code}, {'_id': 0})

    def close(self):
        """Close the MongoDB connection"""
        self.client.close()
