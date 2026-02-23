# performance_app/ml_model.py
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report, confusion_matrix
import joblib
import os
from django.conf import settings

class StudentPerformancePredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        
    def prepare_features(self, df):
        """
        Prepare features for training/prediction
        """
        # Define feature columns
        feature_cols = ['attendance', 'assignment_score', 'quiz_score', 
                       'time_spent', 'forum_posts', 'resources_viewed']
        
        # Make sure all columns exist
        for col in feature_cols:
            if col not in df.columns:
                # Provide default values if columns are missing
                if col in ['attendance', 'assignment_score', 'quiz_score']:
                    df[col] = 75.0  # Default average score
                elif col == 'time_spent':
                    df[col] = 30.0  # Default 30 hours
                else:
                    df[col] = 10  # Default count
        
        # Select features
        X = df[feature_cols].copy()
        self.feature_names = feature_cols
        
        # Handle missing values
        X = X.fillna(X.mean() if len(X) > 0 else 0)
        
        return X
    
    def train_model(self, df, algorithm='random_forest'):
        """
        Train model on the provided dataframe
        """
        # Prepare features
        feature_columns = ['attendance', 'assignment_score', 'quiz_score', 
                          'time_spent', 'forum_posts', 'resources_viewed']
        X = df[feature_columns]
        
        # Create target variable
        if 'performance_category' in df.columns:
            y = df['performance_category']
        else:
            # Create a synthetic target for demonstration
            # Calculate composite score
            composite_score = (
                df['attendance'].fillna(75) * 0.2 +
                df['assignment_score'].fillna(75) * 0.3 +
                df['quiz_score'].fillna(75) * 0.3 +
                (df['time_spent'].fillna(30) / 60 * 100) * 0.1 +
                (df['forum_posts'].fillna(10) / 20 * 100) * 0.05 +
                (df['resources_viewed'].fillna(10) / 50 * 100) * 0.05
            )
            
            # Create labels based on composite score
            conditions = [
                (composite_score >= 85),
                (composite_score >= 70) & (composite_score < 85),
                (composite_score >= 50) & (composite_score < 70),
                (composite_score < 50)
            ]
            labels = ['excellent', 'good', 'average', 'poor']
            y = pd.Series(np.select(conditions, labels, default='average'))
        
        # Check class distribution
        class_counts = y.value_counts()
        min_class_count = class_counts.min()
        
        # Determine optimal CV folds
        cv_folds = min(5, max(2, min_class_count)) if min_class_count >= 2 else None
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Initialize model based on algorithm
        if algorithm == 'random_forest':
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        elif algorithm == 'decision_tree':
            self.model = DecisionTreeClassifier(random_state=42)
        elif algorithm == 'logistic_regression':
            self.model = LogisticRegression(random_state=42, max_iter=1000)
        elif algorithm == 'svm':
            self.model = SVC(random_state=42, probability=True)
        elif algorithm == 'gradient_boosting':
            self.model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        else:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        
        # Train the model
        self.model.fit(X_scaled, y)
        
        # Calculate metrics
        y_pred = self.model.predict(X_scaled)
        
        metrics = {
            'accuracy': accuracy_score(y, y_pred),
            'precision': precision_score(y, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y, y_pred, average='weighted', zero_division=0),
            'f1_score': f1_score(y, y_pred, average='weighted', zero_division=0)
        }
        
        # Only perform cross-validation if we have enough samples
        if cv_folds and min_class_count >= 3:
            try:
                cv_scores = cross_val_score(self.model, X_scaled, y, cv=cv_folds)
                metrics['cv_mean'] = cv_scores.mean()
                metrics['cv_std'] = cv_scores.std()
            except Exception as e:
                print(f"Cross-validation failed: {e}")
                metrics['cv_mean'] = None
                metrics['cv_std'] = None
        else:
            metrics['cv_mean'] = None
            metrics['cv_std'] = None
        
        # Get feature importance
        if hasattr(self.model, 'feature_importances_'):
            self.feature_importance = dict(zip(feature_columns, self.model.feature_importances_))
        else:
            # For models without feature_importances_ (like SVM, LogisticRegression)
            # Use coefficient magnitude as importance
            if hasattr(self.model, 'coef_'):
                importance = np.abs(self.model.coef_).mean(axis=0)
                self.feature_importance = dict(zip(feature_columns, importance))
            else:
                self.feature_importance = {feature: 1/len(feature_columns) for feature in feature_columns}
        
        return metrics, feature_columns

    def create_synthetic_labels(self, df):
        """
        Create synthetic performance labels based on rules
        """
        # Calculate composite score
        composite_score = (
            df['attendance'].fillna(75) * 0.2 +
            df['assignment_score'].fillna(75) * 0.3 +
            df['quiz_score'].fillna(75) * 0.3 +
            (df['time_spent'].fillna(30) / 60 * 100) * 0.1 +
            (df['forum_posts'].fillna(10) / 20 * 100) * 0.05 +
            (df['resources_viewed'].fillna(10) / 50 * 100) * 0.05
        )
        
        # Create labels
        conditions = [
            (composite_score >= 90),
            (composite_score >= 80) & (composite_score < 90),
            (composite_score >= 70) & (composite_score < 80),
            (composite_score >= 60) & (composite_score < 70),
            (composite_score < 60)
        ]
        
        labels = ['excellent', 'good', 'average', 'poor', 'at_risk']
        
        df['performance_label'] = np.select(conditions, labels, default='average')
        
        return df
    
    def predict_batch(self, df):
        """
        Predict performance for batch of students
        """
        predictions = []
        
        try:
            # Prepare features
            X = self.prepare_features(df)
            
            if len(X) == 0:
                return [{'student_id': '', 'prediction': 'Error: No features', 'is_at_risk': False}]
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Make predictions
            if self.model is None:
                # If no model is trained, use rule-based prediction
                predicted_labels = []
                for idx in range(len(df)):
                    prediction = self.rule_based_prediction(df.iloc[idx])
                    predicted_labels.append(prediction)
            else:
                # Use trained model
                try:
                    predicted_labels = self.model.predict(X_scaled)
                except:
                    # Fallback to rule-based
                    predicted_labels = []
                    for idx in range(len(df)):
                        prediction = self.rule_based_prediction(df.iloc[idx])
                        predicted_labels.append(prediction)
            
            # Format predictions
            for idx, label in enumerate(predicted_labels):
                student_id = df.iloc[idx]['student_id'] if 'student_id' in df.columns else f'Student_{idx}'
                
                # Get prediction probability if available
                confidence = 0.85
                if self.model is not None and hasattr(self.model, 'predict_proba'):
                    try:
                        proba = self.model.predict_proba(X_scaled[idx:idx+1])
                        confidence = float(np.max(proba))
                    except:
                        pass
                
                prediction = {
                    'student_id': student_id,
                    'prediction': label.title() if isinstance(label, str) else label,
                    'is_at_risk': label in ['at_risk', 'poor'] if isinstance(label, str) else False,
                    'confidence': confidence
                }
                predictions.append(prediction)
                
        except Exception as e:
            print(f"Error in batch prediction: {str(e)}")
            # Fall back to rule-based prediction
            for idx in range(len(df)):
                try:
                    prediction = self.rule_based_prediction(df.iloc[idx])
                    student_id = df.iloc[idx]['student_id'] if 'student_id' in df.columns else f'Student_{idx}'
                    
                    predictions.append({
                        'student_id': student_id,
                        'prediction': prediction.title(),
                        'is_at_risk': prediction in ['at_risk', 'poor'],
                        'confidence': 0.70
                    })
                except:
                    predictions.append({
                        'student_id': f'Student_{idx}',
                        'prediction': 'Error',
                        'is_at_risk': False,
                        'confidence': 0.0
                    })
        
        return predictions
    
    def rule_based_prediction(self, student_data):
        """
        Rule-based prediction as fallback
        """
        try:
            # Extract values with defaults
            attendance = float(student_data.get('attendance', 75) if pd.notna(student_data.get('attendance', 75)) else 75)
            assignment_score = float(student_data.get('assignment_score', 75) if pd.notna(student_data.get('assignment_score', 75)) else 75)
            quiz_score = float(student_data.get('quiz_score', 75) if pd.notna(student_data.get('quiz_score', 75)) else 75)
            time_spent = float(student_data.get('time_spent', 30) if pd.notna(student_data.get('time_spent', 30)) else 30)
            forum_posts = float(student_data.get('forum_posts', 10) if pd.notna(student_data.get('forum_posts', 10)) else 10)
            resources_viewed = float(student_data.get('resources_viewed', 10) if pd.notna(student_data.get('resources_viewed', 10)) else 10)
            
            # Calculate weighted score
            weighted_score = (
                attendance * 0.2 +
                assignment_score * 0.3 +
                quiz_score * 0.3 +
                min(time_spent / 60 * 100, 100) * 0.1 +
                min(forum_posts / 20 * 100, 100) * 0.05 +
                min(resources_viewed / 50 * 100, 100) * 0.05
            )
            
            if weighted_score >= 85:
                return 'excellent'
            elif weighted_score >= 70:
                return 'good'
            elif weighted_score >= 50:
                return 'average'
            elif weighted_score >= 35:
                return 'poor'
            else:
                return 'at_risk'
        except Exception as e:
            print(f"Error in rule-based prediction: {e}")
            return 'average'
    
    def get_feature_importance(self):
        """
        Get feature importance from model
        """
        if hasattr(self, 'feature_importance') and self.feature_importance:
            importance = self.feature_importance
        elif hasattr(self.model, 'feature_importances_'):
            importance = dict(zip(self.feature_names, self.model.feature_importances_))
        elif hasattr(self.model, 'coef_'):
            importance = dict(zip(self.feature_names, np.abs(self.model.coef_).mean(axis=0)))
        else:
            # Default importance
            importance = {feature: 1/len(self.feature_names) for feature in self.feature_names}
        
        # Sort by importance
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))
    
    def save_model(self, filename):
        """
        Save trained model to file
        """
        # Create models directory if it doesn't exist
        models_dir = os.path.join(settings.MEDIA_ROOT, 'models')
        os.makedirs(models_dir, exist_ok=True)
        
        model_path = os.path.join(models_dir, filename)
        
        # Save model and preprocessing objects
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'feature_names': self.feature_names,
            'feature_importance': self.feature_importance if hasattr(self, 'feature_importance') else {}
        }, model_path)
        
        return model_path
    
    def load_model(self, filepath):
        """
        Load trained model from file
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        saved_data = joblib.load(filepath)
        
        self.model = saved_data['model']
        self.scaler = saved_data['scaler']
        self.label_encoder = saved_data['label_encoder']
        self.feature_names = saved_data['feature_names']
        
        if 'feature_importance' in saved_data:
            self.feature_importance = saved_data['feature_importance']
        
        return True