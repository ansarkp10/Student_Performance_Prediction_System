import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import joblib
import os
from django.conf import settings

class StudentPerformancePredictor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.model = None
        self.model_name = None
        
    def prepare_data(self, df):
        """Prepare data for training"""
        # Create target variable based on scores
        conditions = [
            (df['assignment_score'] >= 85) & (df['quiz_score'] >= 85),
            (df['assignment_score'] >= 70) & (df['quiz_score'] >= 70),
            (df['assignment_score'] >= 60) & (df['quiz_score'] >= 60),
            (df['assignment_score'] >= 50) & (df['quiz_score'] >= 50),
            (df['assignment_score'] < 50) | (df['quiz_score'] < 50)
        ]
        choices = ['excellent', 'good', 'average', 'poor', 'at_risk']
        df['performance'] = np.select(conditions, choices, default='average')
        
        # Features for prediction
        features = ['attendance', 'assignment_score', 'quiz_score', 
                   'time_spent', 'forum_posts', 'resources_viewed']
        
        X = df[features].values
        y = self.label_encoder.fit_transform(df['performance'])
        
        return X, y, features
    
    def train_model(self, df, algorithm='random_forest'):
        """Train a machine learning model"""
        X, y, features = self.prepare_data(df)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Choose algorithm
        algorithms = {
            'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
            'decision_tree': DecisionTreeClassifier(random_state=42),
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
            'svm': SVC(random_state=42, probability=True),
            'gradient_boosting': GradientBoostingClassifier(random_state=42)
        }
        
        self.model_name = algorithm
        self.model = algorithms.get(algorithm, algorithms['random_forest'])
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, average='weighted'),
            'recall': recall_score(y_test, y_pred, average='weighted'),
            'f1': f1_score(y_test, y_pred, average='weighted')
        }
        
        return metrics, features
    
    def predict(self, student_data):
        """Predict performance for a single student"""
        if self.model is None:
            raise ValueError("Model not trained. Please train the model first.")
        
        # Prepare input data
        input_data = np.array([student_data])
        input_scaled = self.scaler.transform(input_data)
        
        # Make prediction
        prediction_encoded = self.model.predict(input_scaled)[0]
        probabilities = self.model.predict_proba(input_scaled)[0]
        
        # Decode prediction
        prediction = self.label_encoder.inverse_transform([prediction_encoded])[0]
        
        # Map to readable labels
        performance_labels = {
            'excellent': 'Excellent (A)',
            'good': 'Good (B)',
            'average': 'Average (C)',
            'poor': 'Poor (D)',
            'at_risk': 'At Risk (F)'
        }
        
        return {
            'prediction': performance_labels.get(prediction, prediction),
            'confidence': max(probabilities) * 100,
            'probabilities': {
                self.label_encoder.inverse_transform([i])[0]: prob * 100 
                for i, prob in enumerate(probabilities)
            },
            'is_at_risk': prediction == 'at_risk'
        }
    
    def predict_batch(self, df):
        """Predict performance for multiple students"""
        results = []
        
        for _, row in df.iterrows():
            student_data = [
                row['attendance'],
                row['assignment_score'],
                row['quiz_score'],
                row['time_spent'],
                row['forum_posts'],
                row['resources_viewed']
            ]
            
            try:
                prediction = self.predict(student_data)
                results.append({
                    'student_id': row['student_id'],
                    'prediction': prediction['prediction'],
                    'confidence': prediction['confidence'],
                    'is_at_risk': prediction['is_at_risk']
                })
            except Exception as e:
                results.append({
                    'student_id': row['student_id'],
                    'prediction': 'Error',
                    'confidence': 0,
                    'is_at_risk': False,
                    'error': str(e)
                })
        
        return results
    
    def save_model(self, filename):
        """Save the trained model"""
        model_path = os.path.join(settings.MEDIA_ROOT, 'models', filename)
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'model_name': self.model_name
        }, model_path)
        
        return model_path
    
    def load_model(self, filepath):
        """Load a trained model"""
        saved_data = joblib.load(filepath)
        self.model = saved_data['model']
        self.scaler = saved_data['scaler']
        self.label_encoder = saved_data['label_encoder']
        self.model_name = saved_data['model_name']