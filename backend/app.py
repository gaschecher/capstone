from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flasgger import Swagger
import pandas as pd
import numpy as np
import joblib
import os
import json
import base64
from pathlib import Path
from database import MONGO_URI, Database

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure Swagger
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/"
}

swagger = Swagger(app, config=swagger_config)

# Load models and scalers
classifier = joblib.load('model/investment_classifier.joblib')
ranker = joblib.load('model/zip_ranker.joblib')
clf_scaler = joblib.load('model/classifier_scaler.joblib')
rank_scaler = joblib.load('model/ranker_scaler.joblib')
model_info = joblib.load('model/model_info.joblib')

# Initialize database connection
db = Database()

def find_nearby_zips(target_zip, all_zips, num_closest=3):
    """Find closest ZIP codes based on numeric proximity"""
    try:
        target = int(target_zip)
        # Convert all zips to integers for comparison
        zip_distances = [(zip_code, abs(int(zip_code) - target)) 
                        for zip_code in all_zips 
                        if zip_code != target_zip]
        # Sort by distance and get the closest ones
        closest_zips = sorted(zip_distances, key=lambda x: x[1])[:num_closest]
        return [zip_code for zip_code, _ in closest_zips]
    except ValueError:
        return []

@app.route('/api/recommendations/<state_code>', methods=['GET'])
def get_state_recommendations(state_code):
    """
    Get ranked zip code recommendations for a state
    ---
    parameters:
      - name: state_code
        in: path
        type: string
        required: true
        description: Two-letter state code (e.g., 'MA')
    responses:
      200:
        description: List of recommended zip codes with investment metrics
      400:
        description: Invalid state code
      500:
        description: Server error
    """
    try:
        # Get data for the requested state from MongoDB
        state_data = db.get_state_data(state_code)
        
        if len(state_data) == 0:
            return jsonify({'error': f'No data available for state {state_code}'}), 404
        
        # Prepare features for models
        features = state_data[['median_home_value', 'median_rent', 'days_pending', 
                             'price_cuts_percent', 'market_heat', 'price_to_rent']]
        
        # Scale features
        clf_features = clf_scaler.transform(features)
        rank_features = rank_scaler.transform(features)
        
        # Get investment scores and rankings
        investment_scores = classifier.predict_proba(clf_features)[:, 1]
        ranking_scores = ranker.predict(rank_features)
        
        # Combine scores
        state_data['investment_score'] = investment_scores
        state_data['ranking_score'] = ranking_scores
        
        # Sort by ranking score
        state_data = state_data.sort_values('ranking_score', ascending=False)
        
        # Prepare response
        recommendations = []
        for _, row in state_data.iterrows():
            recommendations.append({
                'zip_code': row['zip_code'],
                'city': row['city'],
                'state': row['state'],
                'region_id': str(row['region_id']),
                'msa_name': row['msa_name'],
                'median_home_value': float(row['median_home_value']),
                'median_rent': float(row['median_rent']),
                'days_pending': float(row['days_pending']),
                'price_cuts_percent': float(row['price_cuts_percent']),
                'market_heat': float(row['market_heat']),
                'price_to_rent': float(row['price_to_rent']),
                'investment_score': float(row['investment_score']),
                'ranking_score': float(row['ranking_score'])
            })
        
        return jsonify({'recommendations': recommendations})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<zip_code>', methods=['GET'])
def get_zip_analysis(zip_code):
    """
    Get detailed analysis for a specific ZIP code
    ---
    parameters:
      - name: zip_code
        in: path
        type: string
        required: true
        description: 5-digit ZIP code
    responses:
      200:
        description: Detailed investment analysis for the ZIP code
      400:
        description: Invalid ZIP code
      500:
        description: Server error
    """
    try:
        # Format ZIP code
        zip_code = str(zip_code).zfill(5)
        
        # Get data for the requested ZIP code from MongoDB
        zip_info = db.get_zip_info(zip_code)
        
        # Get all ZIP codes for finding nearby ones
        all_zip_data = db.get_zip_data()
        all_zips = all_zip_data['zip_code'].tolist()
        
        # Find nearby ZIP codes
        nearby_zips = find_nearby_zips(zip_code, all_zips)
        
        # Get data for nearby ZIP codes
        nearby_data = []
        for nearby_zip in nearby_zips:
            nearby_info = db.get_zip_info(nearby_zip)
            if nearby_info:
                nearby_data.append(nearby_info)
        
        if not zip_info:
            error_msg = f'No data available for ZIP code {zip_code}'
            if nearby_data:
                error_msg += '. However, we found data for these nearby ZIP codes'
            return jsonify({
                'error': error_msg,
                'nearby_zips': nearby_data
            }), 404
        
        # Calculate percentile ranks for key metrics
        metrics = ['median_home_value', 'median_rent', 'days_pending', 
                  'price_cuts_percent', 'market_heat', 'price_to_rent']
        
        percentiles = {}
        for metric in metrics:
            all_values = all_zip_data[metric]
            value = zip_info[metric]
            percentile = (all_values < value).mean() * 100
            percentiles[f'{metric}_percentile'] = float(percentile)
        
        # Prepare features for models
        features = pd.DataFrame([{
            'median_home_value': zip_info['median_home_value'],
            'median_rent': zip_info['median_rent'],
            'days_pending': zip_info['days_pending'],
            'price_cuts_percent': zip_info['price_cuts_percent'],
            'market_heat': zip_info['market_heat'],
            'price_to_rent': zip_info['price_to_rent']
        }])
        
        # Scale features
        clf_features = clf_scaler.transform(features)
        rank_features = rank_scaler.transform(features)
        
        # Get scores
        investment_score = float(classifier.predict_proba(clf_features)[0, 1])
        ranking_score = float(ranker.predict(rank_features)[0])
        
        # Prepare response in the structure expected by frontend
        response = {
            'city': zip_info['city'],
            'state': zip_info['state'],
            'zip_code': zip_info['zip_code'],
            'msa_name': zip_info['msa_name'],
            'scores': {
                'investment_score': investment_score,
                'ranking_score': ranking_score
            },
            'metrics': {
                'median_home_value': float(zip_info['median_home_value']),
                'median_rent': float(zip_info['median_rent']),
                'days_pending': float(zip_info['days_pending']),
                'price_cuts_percent': float(zip_info['price_cuts_percent']),
                'market_heat': float(zip_info['market_heat']),
                'price_to_rent': float(zip_info['price_to_rent'])
            },
            'percentiles': percentiles,
            'nearby_zips': nearby_data,
            'model_info': model_info
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/msi-analysis/<state_code>', methods=['GET'])
def get_msi_analysis(state_code):
    """
    Return unique MSIs and their investment scores for a given state
    ---
    parameters:
      - name: state_code
        in: path
        type: string
        required: true
        description: Two-letter state code (e.g., 'MA')
    responses:
      200:
        description: List of MSIs with their investment scores
      400:
        description: Invalid state code
      500:
        description: Server error
    """
    try:
        # Get data from MongoDB
        db = Database()
        df = db.get_state_data(state_code.upper())
        
        if df.empty:
            return jsonify({'error': f'No data found for state {state_code}'}), 404

        # Prepare features for models
        features = df[['median_home_value', 'median_rent', 'days_pending', 
                      'price_cuts_percent', 'market_heat', 'price_to_rent']]
        
        # Scale features
        clf_features = clf_scaler.transform(features)
        
        # Get investment scores
        df['investment_score'] = classifier.predict_proba(clf_features)[:, 1]
        
        # Group by region_id and aggregate
        msi_data = df.groupby('region_id').agg({
            'investment_score': 'mean',  # Average investment score for the MSI
            'price_to_rent': 'first',
            'market_heat': 'first',
            'days_pending': 'first',
            'price_cuts_percent': 'first'
        }).reset_index()
        
        # Convert to list of dictionaries
        msi_list = []
        for _, row in msi_data.iterrows():
            try:
                msi_list.append({
                    'msi_name': str(row['region_id']),
                    'investment_score': float(row['investment_score']),
                    'price_to_rent_ratio': float(row['price_to_rent']),
                    'market_heat': float(row['market_heat']),
                    'days_to_pending': float(row['days_pending']),
                    'price_cuts_percent': float(row['price_cuts_percent'])
                })
            except (KeyError, ValueError) as e:
                app.logger.warning(f"Skipping row due to missing/invalid data: {e}")
                continue
        
        return jsonify({'msi_data': msi_list})
        
    except Exception as e:
        app.logger.error(f"Error in get_msi_analysis: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/model-evaluation', methods=['GET'])
def get_model_evaluation():
    """
    Return model evaluation charts and their descriptions
    ---
    responses:
      200:
        description: Model evaluation metrics and visualizations
      500:
        description: Server error
    """
    results_dir = Path(__file__).parent / 'model' / 'results'
    
    if not results_dir.exists():
        return jsonify({'error': 'No evaluation results found'}), 404
        
    charts = []
    chart_order = [
        'confusion_matrix',
        'classification_report',
        'roc_curve',
        'feature_importance',
        'prediction_distribution',
        'score_distribution'
    ]
    
    descriptions = {
        'confusion_matrix': {
            'title': 'Confusion Matrix',
            'description': ('Shows the model\'s prediction accuracy across different investment categories. '
                          'The diagonal represents correct predictions (True Positives and True Negatives), '
                          'while off-diagonal elements show misclassifications (False Positives and False Negatives). '
                          'Brighter colors indicate higher numbers of predictions in each category.')
        },
        'feature_importance': {
            'title': 'Feature Importance',
            'description': ('Displays the relative importance of each feature in the model\'s decision-making process. '
                          'Longer bars indicate features that have more influence on predicting investment potential. '
                          'Price-to-rent ratio and market heat typically show high importance, '
                          'reflecting their strong correlation with investment success.')
        },
        'roc_curve': {
            'title': 'ROC Curve',
            'description': ('The Receiver Operating Characteristic curve shows the trade-off between true positive rate '
                          '(correctly identified good investments) and false positive rate (incorrectly flagged poor investments) '
                          'at various classification thresholds. The area under the curve (AUC) of 0.89 indicates strong '
                          'discriminative ability - the model is good at distinguishing between good and poor investment opportunities.')
        },
        'classification_report': {
            'title': 'Classification Report',
            'description': ('Detailed performance metrics for each investment category:\n'
                          '• Precision: % of predicted good investments that were actually good (avoiding false recommendations)\n'
                          '• Recall: % of actual good investments that were correctly identified (finding opportunities)\n'
                          '• F1-Score: Balanced measure between precision and recall\n'
                          '• Support: Number of samples in each category')
        },
        'prediction_distribution': {
            'title': 'Prediction Distribution',
            'description': ('Shows how confidently the model makes its predictions across different ZIP codes. '
                          'A bimodal distribution (two peaks) suggests the model is good at distinguishing clear cases, '
                          'while predictions in the middle range (0.4-0.6) indicate areas where more careful analysis is needed.')
        },
        'score_distribution': {
            'title': 'Score Distribution',
            'description': ('Visualizes the distribution of final investment scores across all analyzed ZIP codes. '
                          'The shape helps understand market opportunities:\n'
                          '• Scores > 0.7 (30% of areas): Strong investment potential\n'
                          '• Scores 0.5-0.7 (45% of areas): Moderate potential, requires careful analysis\n'
                          '• Scores < 0.5 (25% of areas): Higher risk or lower return potential')
        }
    }
    
    # Get all PNG files in the results directory
    image_files = list(results_dir.glob('*.png'))
    
    # Process each image file
    for image_file in image_files:
        # Get the base name without extension and convert to lowercase for matching
        base_name = image_file.stem.lower().replace(' ', '_')
        
        # Check if we have a description for this chart
        if base_name in descriptions:
            with open(image_file, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
                
            charts.append({
                'image': image_data,
                'title': descriptions[base_name]['title'],
                'description': descriptions[base_name]['description']
            })
    
    # Sort charts according to my predefined order
    def get_chart_order(chart):
        # Get the position in chart_order, or put at the end if not found
        title_key = chart['title'].lower().replace(' ', '_')
        try:
            return chart_order.index(title_key)
        except ValueError:
            return len(chart_order)
    
    return jsonify(sorted(charts, key=get_chart_order))

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
