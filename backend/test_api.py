import requests
import random
import json
import pandas as pd
from datetime import datetime
import logging
import os

# Set up logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/api_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# API Configuration
BASE_URL = "http://localhost:5000/api"

def load_test_data():
    """Load available states and ZIP codes from processed data"""
    df = pd.read_csv('data/processed_zip_data.csv')
    
    # Get available states
    states = sorted(df['state'].unique())
    
    # Get ZIP codes by state
    zip_codes = {state: sorted(df[df['state'] == state]['zip_code'].tolist()) 
                for state in states}
    
    return states, zip_codes

# Load available states and ZIP codes
AVAILABLE_STATES, AVAILABLE_ZIPS = load_test_data()

def test_state_recommendations(state_code=None):
    """Test the state recommendations endpoint"""
    if state_code is None:
        state_code = random.choice(AVAILABLE_STATES)
    
    url = f"{BASE_URL}/recommendations/{state_code}"
    logging.info(f"\n{'='*50}\nTesting State Recommendations: {state_code}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        logging.info(f"Status Code: {response.status_code}")
        
        # Log summary statistics
        recommendations = data.get('recommendations', [])
        logging.info(f"Total Recommendations: {len(recommendations)}")
        
        if recommendations:
            # Calculate average metrics
            avg_home_value = sum(r['median_home_value'] for r in recommendations) / len(recommendations)
            avg_rent = sum(r['median_rent'] for r in recommendations) / len(recommendations)
            avg_investment_score = sum(r['investment_score'] for r in recommendations) / len(recommendations)
            
            logging.info(f"\nState Summary Statistics:")
            logging.info(f"Average Home Value: ${avg_home_value:,.2f}")
            logging.info(f"Average Rent: ${avg_rent:,.2f}")
            logging.info(f"Average Investment Score: {avg_investment_score:.3f}")
            
            # Log top 3 recommendations
            logging.info(f"\nTop 3 Recommendations:")
            for i, rec in enumerate(recommendations[:3], 1):
                logging.info(f"\nRank {i}:")
                logging.info(f"ZIP Code: {rec['zip_code']}")
                logging.info(f"City: {rec['city']}, {rec['state']}")
                logging.info(f"Home Value: ${rec['median_home_value']:,.2f}")
                logging.info(f"Monthly Rent: ${rec['median_rent']:,.2f}")
                logging.info(f"Investment Score: {rec['investment_score']:.3f}")
                logging.info(f"Market Heat: {rec['market_heat']:.1f}")
        
        return {
            'status': 'success',
            'state': state_code,
            'total_recommendations': len(recommendations),
            'sample_data': recommendations[:3] if recommendations else []
        }
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error testing state recommendations: {str(e)}")
        return {
            'status': 'error',
            'state': state_code,
            'error': str(e)
        }

def test_zip_analysis(zip_code=None):
    """Test the ZIP code analysis endpoint"""
    if zip_code is None:
        # Choose a random state and then a random ZIP from that state
        state = random.choice(AVAILABLE_STATES)
        zip_code = random.choice(AVAILABLE_ZIPS[state])
    
    url = f"{BASE_URL}/analysis/{zip_code}"
    logging.info(f"\n{'='*50}\nTesting ZIP Analysis: {zip_code}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        logging.info(f"Status Code: {response.status_code}")
        
        # Log analysis results
        logging.info(f"\nLocation: {data['city']}, {data['state']}")
        logging.info(f"\nKey Metrics:")
        logging.info(f"Median Home Value: ${data['metrics']['median_home_value']:,.2f}")
        logging.info(f"Monthly Rent: ${data['metrics']['median_rent']:,.2f}")
        logging.info(f"Days to Pending: {data['metrics']['days_pending']:.1f}")
        logging.info(f"Price Cuts %: {data['metrics']['price_cuts_percent']:.1f}%")
        logging.info(f"Market Heat: {data['metrics']['market_heat']:.1f}")
        logging.info(f"Price-to-Rent Ratio: {data['metrics']['price_to_rent']:.2f}")
        logging.info(f"\nScores:")
        logging.info(f"Investment Score: {data['scores']['investment_score']:.3f}")
        logging.info(f"Ranking Score: {data['scores']['ranking_score']:.3f}")
        
        return {
            'status': 'success',
            'zip_code': zip_code,
            'data': data
        }
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Error testing ZIP analysis: {str(e)}")
        return {
            'status': 'error',
            'zip_code': zip_code,
            'error': str(e)
        }

def run_random_tests(num_tests=5):
    """Run a series of random tests on both endpoints"""
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'state_tests': [],
        'zip_tests': []
    }
    
    logging.info(f"\nRunning {num_tests} random tests for each endpoint...")
    
    # Test state recommendations
    for _ in range(num_tests):
        state = random.choice(AVAILABLE_STATES)
        result = test_state_recommendations(state)
        test_results['state_tests'].append(result)
    
    # Test ZIP analysis
    for _ in range(num_tests):
        state = random.choice(AVAILABLE_STATES)
        zip_code = random.choice(AVAILABLE_ZIPS[state])
        result = test_zip_analysis(zip_code)
        test_results['zip_tests'].append(result)
    
    # Save results
    results_dir = 'test_results'
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
    
    filename = os.path.join(results_dir, f'api_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    with open(filename, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    logging.info(f"\nTest results saved to {filename}")
    return test_results

if __name__ == "__main__":
    logging.info("Starting API Tests")
    
    # First make sure we have data
    if not AVAILABLE_STATES or not AVAILABLE_ZIPS:
        logging.error("No test data available. Please run data_preprocessing.py first.")
        exit(1)
    
    logging.info(f"Found {len(AVAILABLE_STATES)} states with data")
    logging.info(f"Total ZIP codes available: {sum(len(zips) for zips in AVAILABLE_ZIPS.values())}")
    
    # Start the Flask server if it's not running
    try:
        requests.get(f"{BASE_URL}/recommendations/{AVAILABLE_STATES[0]}")
    except requests.exceptions.ConnectionError:
        logging.error("API server is not running. Please start app.py first.")
        exit(1)
    
    # Run random tests
    results = run_random_tests(num_tests=5)
    
    logging.info("API Tests Complete")
