import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt

# Load models
classifier = joblib.load('model/investment_classifier.joblib')
ranker = joblib.load('model/zip_ranker.joblib')

# Generate a larger test dataset (1000 samples)
np.random.seed(42)
n_samples = 1000

# Generate features that match my training data distribution
test_data = pd.DataFrame({
    'median_home_value': np.random.uniform(300000, 2000000, n_samples),
    'median_rent': np.random.uniform(2000, 6000, n_samples),
    'days_pending': np.random.uniform(10, 45, n_samples),
    'price_cuts_percent': np.random.uniform(5, 25, n_samples),
    'market_heat': np.random.uniform(60, 95, n_samples)
})

# Calculate price to rent ratio
test_data['price_to_rent'] = test_data['median_home_value'] / (test_data['median_rent'] * 12)

# Get predictions
predictions = classifier.predict(test_data)
probabilities = classifier.predict_proba(test_data)
scores = ranker.predict(test_data)

# Analyze results
total_recommended = np.sum(predictions == 1)
percent_recommended = (total_recommended / n_samples) * 100

print("\nPrediction Analysis:")
print(f"Total samples: {n_samples}")
print(f"Recommended properties: {total_recommended}")
print(f"Percentage recommended: {percent_recommended:.2f}%")

# Analyze confidence scores
confidence_scores = np.max(probabilities, axis=1)
print("\nConfidence Score Analysis:")
print(f"Average confidence: {confidence_scores.mean():.2f}")
print(f"Median confidence: {np.median(confidence_scores):.2f}")
print("\nConfidence Distribution:")
print(pd.qcut(confidence_scores, q=5).value_counts())

# Analyze investment scores
print("\nInvestment Score Analysis:")
print(f"Average score: {scores.mean():.2f}")
print(f"Score range: {scores.min():.2f} to {scores.max():.2f}")

# Plot distributions
plt.figure(figsize=(12, 4))

# Plot 1: Recommendation Distribution
plt.subplot(131)
plt.bar(['Not Recommended', 'Recommended'], 
        [np.sum(predictions == 0), np.sum(predictions == 1)])
plt.title('Recommendation Distribution')
plt.ylabel('Count')

# Plot 2: Confidence Score Distribution
plt.subplot(132)
plt.hist(confidence_scores, bins=20)
plt.title('Confidence Score Distribution')
plt.xlabel('Confidence')
plt.ylabel('Count')

# Plot 3: Investment Score Distribution
plt.subplot(133)
plt.hist(scores, bins=20)
plt.title('Investment Score Distribution')
plt.xlabel('Score')
plt.ylabel('Count')

plt.tight_layout()
plt.savefig('model/prediction_analysis.png')
plt.close()

# Analyze relationship between features and recommendations
print("\nFeature Analysis for Recommended Properties:")
recommended_data = test_data[predictions == 1]
not_recommended_data = test_data[predictions == 0]

for column in test_data.columns:
    print(f"\n{column}:")
    print(f"Recommended - Mean: {recommended_data[column].mean():.2f}, Median: {recommended_data[column].median():.2f}")
    print(f"Not Recommended - Mean: {not_recommended_data[column].mean():.2f}, Median: {not_recommended_data[column].median():.2f}")
