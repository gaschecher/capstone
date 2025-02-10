import pandas as pd
import numpy as np
import os
import json
import re
from database import Database

def normalize_city_name(name):
    """Normalize city name for better matching"""
    if pd.isna(name):
        return ''
    # Convert to lowercase and remove special characters
    name = re.sub(r'[^a-zA-Z\s]', '', name.lower())
    # Remove common suffixes
    name = re.sub(r'\s+(city|town|village|cdp|municipality)\s*$', '', name)
    # Remove extra whitespace
    name = ' '.join(name.split())
    return name

def load_zip_cbsa_mapping(data_dir=None):
    """Load ZIP-CBSA mapping from local file"""
    if data_dir is None:
        data_dir = "backend/data"
    
    mapping_file = os.path.join(data_dir, "ZIP_CBSA_122024.xlsx")
    print(f"Loading ZIP-CBSA mapping data from: {mapping_file}")
    
    # Read Excel file with openpyxl engine
    df = pd.read_excel(mapping_file, engine='openpyxl')
    
    # Keep only residential zip codes with significant residential ratio
    df = df[df['RES_RATIO'] > 0.5]
    
    # Keep necessary columns and rename
    df = df[['ZIP', 'CBSA', 'USPS_ZIP_PREF_CITY', 'USPS_ZIP_PREF_STATE']]
    df.columns = ['zip_code', 'cbsa_code', 'city', 'state']
    
    # Ensure zip_code and cbsa_code are strings with proper formatting
    df['zip_code'] = df['zip_code'].astype(str).str.zfill(5)
    df['cbsa_code'] = df['cbsa_code'].astype(str).str.zfill(5)
    
    # Remove non-metro areas (CBSA code 99999)
    df = df[df['cbsa_code'] != '99999']
    
    # Normalize city names
    df['normalized_city'] = df['city'].apply(normalize_city_name)
    
    return df

def load_zillow_data(data_dir=None):
    """Load and preprocess Zillow datasets at MSA level"""
    if data_dir is None:
        data_dir = "backend/zillow-data"
    print(f"Loading Zillow MSA data from: {data_dir}")
    
    # Load home values
    home_values = pd.read_csv(os.path.join(data_dir, 'zillow_home_value_index.csv'))
    home_values = home_values[home_values['RegionType'] == 'msa']
    value_cols = [col for col in home_values.columns if col.startswith('20')]
    latest_value_col = sorted(value_cols)[-1]
    home_values = home_values[['RegionID', 'RegionName', 'StateName', latest_value_col]]
    home_values = home_values.rename(columns={latest_value_col: 'median_home_value'})
    
    print("\nFirst few rows of home_values:")
    print(home_values[['RegionID', 'RegionName']].head())
    
    # Extract city and state from RegionName
    home_values['city'] = home_values['RegionName'].str.split(',').str[0].str.strip()
    home_values['state'] = home_values['RegionName'].str.split(',').str[1].str.strip()
    
    # Normalize city names for matching
    home_values['normalized_city'] = home_values['city'].apply(normalize_city_name)
    
    # Load rents (values are in hundreds of dollars)
    rents = pd.read_csv(os.path.join(data_dir, 'zillow_observed_rent_index.csv'))
    rents = rents[rents['RegionType'] == 'msa']
    rent_cols = [col for col in rents.columns if col.startswith('20')]
    latest_rent_col = sorted(rent_cols)[-1]
    rents = rents[['RegionID', latest_rent_col]]
    rents = rents.rename(columns={latest_rent_col: 'median_rent'})
    # Convert rent from hundreds to actual dollars
    rents['median_rent'] = rents['median_rent'] * 100
    
    print("\nFirst few rows of rents:")
    print(rents.head())
    
    # Load days to pending
    days = pd.read_csv(os.path.join(data_dir, 'days_to_pending.csv'))
    days = days[days['RegionType'] == 'msa']
    days_cols = [col for col in days.columns if col.startswith('20')]
    latest_days_col = sorted(days_cols)[-1]
    days = days[['RegionID', latest_days_col]]
    days = days.rename(columns={latest_days_col: 'days_pending'})
    
    print("\nFirst few rows of days:")
    print(days.head())
    
    # Load price cuts
    cuts = pd.read_csv(os.path.join(data_dir, 'share_of_listings_with_price_cut.csv'))
    cuts = cuts[cuts['RegionType'] == 'msa']
    cuts_cols = [col for col in cuts.columns if col.startswith('20')]
    latest_cuts_col = sorted(cuts_cols)[-1]
    cuts = cuts[['RegionID', latest_cuts_col]]
    cuts = cuts.rename(columns={latest_cuts_col: 'price_cuts_percent'})
    
    print("\nFirst few rows of cuts:")
    print(cuts.head())
    
    # Load market heat
    heat = pd.read_csv(os.path.join(data_dir, 'market_heat_index.csv'))
    heat = heat[heat['RegionType'] == 'msa']
    heat_cols = [col for col in heat.columns if col.startswith('20')]
    latest_heat_col = sorted(heat_cols)[-1]
    heat = heat[['RegionID', latest_heat_col]]
    heat = heat.rename(columns={latest_heat_col: 'market_heat'})
    
    print("\nFirst few rows of heat:")
    print(heat.head())
    
    # Merge all datasets
    print("Merging Zillow datasets...")
    msa_data = home_values.merge(rents, on='RegionID', how='inner')\
                         .merge(days, on='RegionID', how='inner')\
                         .merge(cuts, on='RegionID', how='inner')\
                         .merge(heat, on='RegionID', how='inner')
    
    print("\nColumns of msa_data:")
    print(msa_data.columns)
    
    print("\nFirst few rows of msa_data:")
    print(msa_data.head())
    
    # Calculate price to rent ratio
    msa_data['price_to_rent'] = msa_data['median_home_value'] / (msa_data['median_rent'] * 12)
    
    # Clean data
    msa_data = msa_data.dropna()
    msa_data = msa_data[msa_data['median_home_value'] > 0]
    msa_data = msa_data[msa_data['median_rent'] > 0]
    msa_data = msa_data[msa_data['days_pending'] > 0]
    msa_data = msa_data[msa_data['market_heat'] > 0]
    
    return msa_data

def process_and_map_data():
    """Process Zillow MSA data and map it to zip codes"""
    # Get data directories from environment or use defaults
    data_dir = os.getenv('DATA_DIR', "backend/data")
    zillow_dir = os.getenv('ZILLOW_DIR', "backend/zillow-data")
    
    # Load ZIP-CBSA mapping
    zip_data = load_zip_cbsa_mapping(data_dir)
    
    # Load and process Zillow MSA data
    msa_data = load_zillow_data(zillow_dir)
    
    print("Mapping ZIP codes to MSA data...")
    # Create a mapping of CBSA codes to their primary cities
    cbsa_cities = {}
    for cbsa_code in zip_data['cbsa_code'].unique():
        # Get all cities in this CBSA
        cbsa_zips = zip_data[zip_data['cbsa_code'] == cbsa_code]
        # Count occurrences of each normalized city name
        city_counts = cbsa_zips['normalized_city'].value_counts()
        if len(city_counts) > 0:
            # Get the most common city
            primary_city = city_counts.index[0]
            # Get a sample record for this city to get the state
            sample_record = cbsa_zips[cbsa_zips['normalized_city'] == primary_city].iloc[0]
            cbsa_cities[cbsa_code] = {
                'normalized_city': primary_city,
                'state': sample_record['state']
            }
    
    # Find matching MSAs for each CBSA
    cbsa_to_msa = {}
    for cbsa_code, city_info in cbsa_cities.items():
        # Find MSAs that match both the normalized city name and state
        matches = msa_data[
            (msa_data['normalized_city'] == city_info['normalized_city']) &
            (msa_data['state'] == city_info['state'])
        ]
        if len(matches) > 0:
            cbsa_to_msa[cbsa_code] = matches.iloc[0]['RegionName']
    
    # Add MSA names to ZIP data
    zip_data['msa_name'] = zip_data['cbsa_code'].map(cbsa_to_msa)
    
    # Merge with MSA data
    zip_data = zip_data.merge(msa_data,
                             left_on='msa_name',
                             right_on='RegionName',
                             how='inner')
    
    # Select and clean final columns
    zip_data = zip_data[[
        'zip_code', 'city_x', 'state_x', 'RegionID', 'RegionName',
        'median_home_value', 'median_rent', 'days_pending',
        'price_cuts_percent', 'market_heat', 'price_to_rent'
    ]]
    zip_data.columns = [
        'zip_code', 'city', 'state', 'region_id', 'msa_name',
        'median_home_value', 'median_rent', 'days_pending',
        'price_cuts_percent', 'market_heat', 'price_to_rent'
    ]
    
    # Round numeric columns
    zip_data['median_home_value'] = zip_data['median_home_value'].round(2)
    zip_data['median_rent'] = zip_data['median_rent'].round(2)
    zip_data['days_pending'] = zip_data['days_pending'].round(1)
    zip_data['price_cuts_percent'] = zip_data['price_cuts_percent'].round(1)
    zip_data['market_heat'] = zip_data['market_heat'].round(1)
    zip_data['price_to_rent'] = zip_data['price_to_rent'].round(2)
    
    # Save processed data
    output_dir = "data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print("Saving processed data...")
    # Save main dataset
    zip_data.to_csv(os.path.join(output_dir, "processed_zip_data.csv"), index=False)
    
    # Create and save state lookup for faster API access
    state_data = {}
    for state in zip_data['state'].unique():
        state_data[state] = zip_data[zip_data['state'] == state].to_dict('records')
    
    with open(os.path.join(output_dir, "state_lookup.json"), 'w') as f:
        json.dump(state_data, f, indent=2)
    
    print(f"Processing complete! Dataset contains {len(zip_data)} zip codes across {len(zip_data['state'].unique())} states")
    
    # Additionally save to MongoDB
    try:
        from database import Database
        print("Saving data to MongoDB...")
        db = Database()
        db.initialize_collections(zip_data, state_data)
        print("Successfully saved data to MongoDB!")
    except Exception as e:
        print(f"Warning: Failed to save to MongoDB: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()
    
    return zip_data

if __name__ == "__main__":
    process_and_map_data()
