import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import joblib
import os

def load_and_preprocess_data():
    """
    Load Zillow datasets and preprocess them
    Returns preprocessed data for each region (MSA)
    """
    data_dir = os.path.join(os.path.dirname(__file__), 'zillow-data')
    
    # Load home values
    home_values = pd.read_csv(os.path.join(data_dir, 'zillow_home_value_index.csv'))
    home_values = home_values[home_values['RegionType'] == 'msa']  # Keep only MSA level
    value_cols = [col for col in home_values.columns if col.startswith('20')]  # Get all year columns
    latest_value_col = sorted(value_cols)[-1]  # Get most recent date
    home_values = home_values[['RegionID', 'RegionName', 'StateName', latest_value_col]]
    home_values = home_values.rename(columns={latest_value_col: 'median_home_value'})
    
    # Load rents
    rents = pd.read_csv(os.path.join(data_dir, 'zillow_observed_rent_index.csv'))
    rents = rents[rents['RegionType'] == 'msa']
    rent_cols = [col for col in rents.columns if col.startswith('20')]
    latest_rent_col = sorted(rent_cols)[-1]
    rents = rents[['RegionID', latest_rent_col]]
    rents = rents.rename(columns={latest_rent_col: 'median_rent'})
    
    # Load days to pending
    days = pd.read_csv(os.path.join(data_dir, 'days_to_pending.csv'))
    days = days[days['RegionType'] == 'msa']
    days_cols = [col for col in days.columns if col.startswith('20')]
    latest_days_col = sorted(days_cols)[-1]
    days = days[['RegionID', latest_days_col]]
    days = days.rename(columns={latest_days_col: 'days_pending'})
    
    # Load price cuts
    cuts = pd.read_csv(os.path.join(data_dir, 'share_of_listings_with_price_cut.csv'))
    cuts = cuts[cuts['RegionType'] == 'msa']
    cuts_cols = [col for col in cuts.columns if col.startswith('20')]
    latest_cuts_col = sorted(cuts_cols)[-1]
    cuts = cuts[['RegionID', latest_cuts_col]]
    cuts = cuts.rename(columns={latest_cuts_col: 'price_cuts_percent'})
    
    # Load market heat
    heat = pd.read_csv(os.path.join(data_dir, 'market_heat_index.csv'))
    heat = heat[heat['RegionType'] == 'msa']
    heat_cols = [col for col in heat.columns if col.startswith('20')]
    latest_heat_col = sorted(heat_cols)[-1]
    heat = heat[['RegionID', latest_heat_col]]
    heat = heat.rename(columns={latest_heat_col: 'market_heat'})
    
    # Merge all datasets
    data = home_values.merge(rents, on='RegionID', how='inner')\
                     .merge(days, on='RegionID', how='inner')\
                     .merge(cuts, on='RegionID', how='inner')\
                     .merge(heat, on='RegionID', how='inner')
    
    # Clean data
    data = data.dropna()  # Remove any rows with missing values
    
    # Extract state and zip from region name (e.g., "Miami, FL")
    data['state'] = data['RegionName'].str.extract(r', (\w{2})$')
    data['zip_code'] = data['RegionID'].astype(str)  # Use RegionID as zip code for now
    
    # Remove any rows with invalid data
    data = data[data['median_home_value'] > 0]
    data = data[data['median_rent'] > 0]
    data = data[data['days_pending'] > 0]
    data = data[data['market_heat'] > 0]
    
    return data

def prepare_features_and_target(data):
    """Prepare features and target variables"""
    # Create target variable
    data['price_to_rent'] = data['median_home_value'] / (data['median_rent'] * 12)
    
    # Calculate scores for each metric (0-100)
    ptr_score = 100 - data['price_to_rent'].rank(pct=True) * 100  # Lower is better
    heat_score = data['market_heat'].rank(pct=True) * 100         # Higher is better
    days_score = 100 - data['days_pending'].rank(pct=True) * 100  # Lower is better
    cuts_score = 100 - data['price_cuts_percent'].rank(pct=True) * 100  # Lower is better
    
    # Combined score (weighted average)
    data['investment_score'] = (
        ptr_score * 0.4 +    # Price to rent ratio (40% weight)
        heat_score * 0.3 +   # Market heat (30% weight)
        days_score * 0.15 +  # Days pending (15% weight)
        cuts_score * 0.15    # Price cuts (15% weight)
    )
    
    # Good investment if total score is in top 40%
    score_threshold = data['investment_score'].quantile(0.6)  # Top 40%
    data['is_good_investment'] = data['investment_score'] >= score_threshold
    
    # Features for classification
    X = data[[
        'median_home_value', 'median_rent', 'days_pending',
        'price_cuts_percent', 'market_heat', 'price_to_rent'
    ]]
    y_clf = data['is_good_investment']
    y_reg = data['investment_score']
    
    return X, y_clf, y_reg

def train_investment_classifier(X_train, y_train):
    """
    Trains model to classify if a zip code is good for investment
    Based on price-to-rent ratio, market heat, and price stability
    """
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns)
    
    # Train with more conservative parameters to prevent overfitting
    clf = RandomForestClassifier(
        n_estimators=50,  # Reduced from 100
        max_depth=5,      # Reduced from 10
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42
    )
    clf.fit(X_train_scaled, y_train)
    
    return clf, scaler

def train_ranking_model(X_train, y_train):
    """
    Trains model to score/rank zip codes within each state
    Based on combined investment metrics
    """
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_train_scaled = pd.DataFrame(X_train_scaled, columns=X_train.columns)
    
    # Train with more conservative parameters
    ranker = RandomForestRegressor(
        n_estimators=50,
        max_depth=5,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42
    )
    ranker.fit(X_train_scaled, y_train)
    
    return ranker, scaler

def train_and_save_models():
    """Train both models and save them"""
    # Load and prepare data
    data = load_and_preprocess_data()
    X, y_clf, y_reg = prepare_features_and_target(data)
    
    # Split data into train/test sets
    X_train, X_test, y_clf_train, y_clf_test, y_reg_train, y_reg_test = train_test_split(
        X, y_clf, y_reg, test_size=0.2, random_state=42
    )
    
    # Train classification model
    clf, clf_scaler = train_investment_classifier(X_train, y_clf_train)
    X_test_scaled = clf_scaler.transform(X_test)
    clf_score = clf.score(X_test_scaled, y_clf_test)
    print(f"Classification Model Accuracy: {clf_score:.2f}")
    
    # Train ranking model
    ranker, rank_scaler = train_ranking_model(X_train, y_reg_train)
    X_test_scaled = rank_scaler.transform(X_test)
    rank_score = ranker.score(X_test_scaled, y_reg_test)
    print(f"Ranking Model R² Score: {rank_score:.2f}")
    
    # Create model directory if it doesn't exist
    os.makedirs('model', exist_ok=True)
    
    # Save models and scalers
    joblib.dump(clf, 'model/investment_classifier.joblib')
    joblib.dump(ranker, 'model/zip_ranker.joblib')
    joblib.dump(clf_scaler, 'model/classifier_scaler.joblib')
    joblib.dump(rank_scaler, 'model/ranker_scaler.joblib')
    
    # Save feature names and preprocessing info
    model_info = {
        'feature_names': X.columns.tolist(),
        'target_thresholds': {
            'price_to_rent_median': float(X_test['price_to_rent'].median()),
            'market_heat_median': float(X_test['market_heat'].median()),
            'days_pending_median': float(X_test['days_pending'].median())
        }
    }
    joblib.dump(model_info, 'model/model_info.joblib')
    
    # Save test data for evaluation
    test_data = pd.DataFrame({
        'X_test': [X_test.to_dict()],
        'y_clf_test': [y_clf_test.to_dict()],
        'y_reg_test': [y_reg_test.to_dict()]
    })
    joblib.dump(test_data, 'model/test_data.joblib')

if __name__ == '__main__':
    train_and_save_models()
