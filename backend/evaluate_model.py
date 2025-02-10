import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Create results directory if it doesn't exist
if not os.path.exists('model/results'):
    os.makedirs('model/results')

def plot_confusion_matrix(y_true, y_pred):
    """Plot confusion matrix"""
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
    plt.title('Confusion Matrix')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.savefig('model/results/confusion_matrix.png')
    plt.close()

def plot_feature_importance(classifier, feature_names):
    """Plot feature importance"""
    importance = classifier.feature_importances_
    indices = np.argsort(importance)[::-1]
    
    plt.figure(figsize=(10, 6))
    plt.title('Feature Importances')
    plt.bar(range(len(importance)), importance[indices])
    plt.xticks(range(len(importance)), [feature_names[i] for i in indices], rotation=45)
    plt.tight_layout()
    plt.savefig('model/results/feature_importance.png')
    plt.close()

def plot_score_distribution(scores, recommendations, title="Investment Score Distribution"):
    """Plot investment score distribution by recommendation"""
    plt.figure(figsize=(10, 6))
    plt.hist([
        scores[recommendations],
        scores[~recommendations]
    ], label=['Recommended', 'Not Recommended'], bins=30, alpha=0.6)
    plt.title(title)
    plt.xlabel('Investment Score')
    plt.ylabel('Count')
    plt.legend()
    plt.tight_layout()
    plt.savefig('model/results/score_distribution.png')
    plt.close()

def evaluate_models():
    """Evaluate both classifier and ranking models"""
    # Load models and scalers
    classifier = joblib.load('model/investment_classifier.joblib')
    ranker = joblib.load('model/zip_ranker.joblib')
    clf_scaler = joblib.load('model/classifier_scaler.joblib')
    rank_scaler = joblib.load('model/ranker_scaler.joblib')
    
    # Load test data
    test_data = joblib.load('model/test_data.joblib')
    X_test = pd.DataFrame(test_data['X_test'].iloc[0])
    y_true = pd.Series(test_data['y_clf_test'].iloc[0])
    y_reg_true = pd.Series(test_data['y_reg_test'].iloc[0])
    
    # Scale features
    X_test_scaled_clf = clf_scaler.transform(X_test)
    X_test_scaled_rank = rank_scaler.transform(X_test)
    
    # Get predictions
    y_pred = classifier.predict(X_test_scaled_clf)
    y_proba = classifier.predict_proba(X_test_scaled_clf)
    investment_scores = ranker.predict(X_test_scaled_rank)
    
    # Generate plots
    plot_confusion_matrix(y_true, y_pred)
    plot_feature_importance(classifier, X_test.columns)
    plot_score_distribution(investment_scores, y_pred)
    
    # Print classification report
    print("\nClassification Report:")
    print(classification_report(y_true, y_pred))
    
    # Analyze confidence scores
    confidence_scores = np.max(y_proba, axis=1)
    print("\nConfidence Score Analysis:")
    print(f"Average confidence: {confidence_scores.mean():.2f}")
    print(f"Median confidence: {np.median(confidence_scores):.2f}")
    
    # Analyze investment scores
    print("\nInvestment Score Analysis:")
    print(f"Average predicted score: {investment_scores.mean():.2f}")
    print(f"Average true score: {y_reg_true.mean():.2f}")
    print(f"Score correlation: {np.corrcoef(investment_scores, y_reg_true)[0,1]:.2f}")
    
    # Save detailed results
    results = pd.DataFrame({
        'true_label': y_true,
        'predicted_label': y_pred,
        'confidence_score': confidence_scores,
        'predicted_investment_score': investment_scores,
        'true_investment_score': y_reg_true
    })
    results.to_csv('model/results/evaluation_results.csv', index=False)

if __name__ == '__main__':
    evaluate_models()
