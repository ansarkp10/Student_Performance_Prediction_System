# performance_app/train_model.py
import pandas as pd
import numpy as np
import os
import sys

# Get the correct path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # This should be student_performance folder

# Add to Python path
sys.path.append(project_root)

# Setup Django properly
import django
from django.conf import settings

if not settings.configured:
    # Try to find the settings
    settings_path = os.path.join(project_root, 'student_performance', 'settings.py')
    
    if os.path.exists(settings_path):
        # Nested structure
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_performance.student_performance.settings')
    else:
        # Try other locations
        settings_path = os.path.join(project_root, 'settings.py')
        if os.path.exists(settings_path):
            # Simple structure
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_performance.settings')
        else:
            print("ERROR: Could not find settings.py")
            sys.exit(1)

django.setup()

# Now import Django models
from performance_app.ml_model import StudentPerformancePredictor
from performance_app.models import Course, Student, PredictionModel
from django.contrib.auth.models import User
from datetime import datetime

def load_and_train_csv(csv_file_path=None, course_id=None):
    """
    Load CSV data and train the model
    """
    if csv_file_path is None:
        # Try to find CSV in dataset folder
        csv_file_path = os.path.join(project_root, 'dataset', 'student_dataset.csv')
    
    print(f"Looking for CSV at: {csv_file_path}")
    print(f"File exists: {os.path.exists(csv_file_path)}")
    
    if not os.path.exists(csv_file_path):
        print("ERROR: CSV file not found!")
        print("Please provide the full path to your CSV file.")
        return None, None, None
    
    print(f"Loading CSV file: {csv_file_path}")
    
    # Load CSV
    df = pd.read_csv(csv_file_path)
    print(f"Loaded {len(df)} records")
    
    # Check if we have all required features
    required_columns = [
        'student_id', 'attendance', 'assignment_score', 
        'quiz_score', 'time_spent', 'forum_posts', 'resources_viewed'
    ]
    
    # Add missing columns if they don't exist
    for col in required_columns:
        if col not in df.columns:
            if col == 'student_id':
                # Create sequential student IDs
                df['student_id'] = [f'S{str(i+1).zfill(3)}' for i in range(len(df))]
            else:
                # Fill with default values
                if 'score' in col or 'attendance' in col:
                    df[col] = np.random.uniform(60, 100, len(df))
                elif 'time' in col:
                    df[col] = np.random.uniform(20, 60, len(df))
                else:
                    df[col] = np.random.randint(0, 20, len(df))
    
    # Display data info
    print("\nData Overview:")
    print(f"Total records: {len(df)}")
    print("\nFirst 5 records:")
    print(df.head())
    print("\nData statistics:")
    print(df.describe())
    
    # Prepare features for training
    features = ['attendance', 'assignment_score', 'quiz_score', 
                'time_spent', 'forum_posts', 'resources_viewed']
    
    # Create training data
    X = df[features].copy()
    
    # For demonstration, let's create labels based on rules
    # Define performance categories based on weighted scores
    weights = {
        'attendance': 0.2,
        'assignment_score': 0.3,
        'quiz_score': 0.3,
        'time_spent': 0.1,
        'forum_posts': 0.05,
        'resources_viewed': 0.05
    }
    
    # Calculate weighted score
    weighted_scores = (
        X['attendance'] * weights['attendance'] +
        X['assignment_score'] * weights['assignment_score'] +
        X['quiz_score'] * weights['quiz_score'] +
        (X['time_spent'] / 60 * 100) * weights['time_spent'] +
        (X['forum_posts'] / 20 * 100) * weights['forum_posts'] +
        (X['resources_viewed'] / 50 * 100) * weights['resources_viewed']
    )
    
    # Create labels based on weighted scores
    y = pd.cut(weighted_scores, 
               bins=[0, 60, 70, 80, 90, 100],
               labels=['at_risk', 'poor', 'average', 'good', 'excellent'])
    
    # Add labels to DataFrame
    df['performance_label'] = y
    
    print("\nPerformance Distribution:")
    print(y.value_counts().sort_index())
    
    # Initialize and train predictor
    predictor = StudentPerformancePredictor()
    
    # Add labels to training data
    training_df = X.copy()
    training_df['performance_label'] = y
    
    # Try different algorithms
    algorithms = ['random_forest', 'gradient_boosting', 'decision_tree']
    best_accuracy = 0
    best_model = None
    
    for algorithm in algorithms:
        print(f"\nTraining with {algorithm}...")
        metrics, feature_names = predictor.train_model(training_df, algorithm)
        
        if metrics['accuracy'] > best_accuracy:
            best_accuracy = metrics['accuracy']
            best_model = algorithm
    
    print(f"\nBest algorithm: {best_model} with accuracy: {best_accuracy:.2%}")
    
    # Make predictions
    predictions = predictor.predict_batch(df)
    
    # Display sample predictions
    print("\nSample Predictions:")
    for i, pred in enumerate(predictions[:5]):
        print(f"{i+1}. Student {pred['student_id']}: {pred['prediction']} (At Risk: {pred['is_at_risk']})")
    
    # Save the trained model
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    model_filename = f"trained_model_{timestamp}.joblib"
    model_path = predictor.save_model(model_filename)
    
    print(f"\nModel saved to: {model_path}")
    
    # Optionally save predictions back to CSV
    df['predicted_performance'] = [p['prediction'].split()[0].lower() for p in predictions]
    df['is_at_risk'] = [p['is_at_risk'] for p in predictions]
    
    output_csv = csv_file_path.replace('.csv', '_with_predictions.csv')
    df.to_csv(output_csv, index=False)
    print(f"Predictions saved to: {output_csv}")
    
    return predictor, df, model_path

def import_to_database(df, course_id=None):
    """
    Import CSV data with predictions to Django database
    """
    # Get or create a default course
    if course_id:
        course = Course.objects.get(id=course_id)
    else:
        # Get or create default instructor
        instructor, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@university.edu'}
        )
        instructor.set_password('admin123')
        instructor.save()
        
        # Get or create default course
        course, _ = Course.objects.get_or_create(
            course_code="CS101",
            defaults={
                'course_name': 'Introduction to Computer Science',
                'instructor': instructor,
                'description': 'Default course for imported students'
            }
        )
    
    # Import students
    imported_count = 0
    for _, row in df.iterrows():
        try:
            student, created = Student.objects.update_or_create(
                student_id=row['student_id'],
                defaults={
                    'first_name': row.get('first_name', 'Unknown'),
                    'last_name': row.get('last_name', 'Student'),
                    'email': row.get('email', f"{row['student_id']}@university.edu"),
                    'course': course,
                    'attendance': row.get('attendance', 0.0),
                    'assignment_score': row.get('assignment_score', 0.0),
                    'quiz_score': row.get('quiz_score', 0.0),
                    'time_spent': row.get('time_spent', 0.0),
                    'forum_posts': row.get('forum_posts', 0),
                    'resources_viewed': row.get('resources_viewed', 0),
                    'predicted_performance': row.get('predicted_performance', ''),
                    'is_at_risk': row.get('is_at_risk', False),
                }
            )
            imported_count += 1
            
            if created:
                print(f"Created: {student.student_id}")
            else:
                print(f"Updated: {student.student_id}")
                
        except Exception as e:
            print(f"Error importing {row.get('student_id', 'Unknown')}: {str(e)}")
    
    print(f"\nSuccessfully imported/updated {imported_count} students to course: {course.course_name}")
    return imported_count

if __name__ == "__main__":
    # Try to find CSV
    csv_path = os.path.join(project_root, 'dataset', 'student_dataset.csv')
    
    if not os.path.exists(csv_path):
        print("ERROR: CSV file not found at:", csv_path)
        print("Please place your student_dataset.csv in the dataset folder")
        sys.exit(1)
    
    # Load and train
    predictor, df_with_predictions, model_path = load_and_train_csv(csv_path)
    
    if predictor:
        # Ask if user wants to import to database
        import_to_db = input("\nDo you want to import to database? (yes/no): ").strip().lower()
        
        if import_to_db == 'yes':
            # Get course ID if available
            course_id_input = input("Enter course ID (press Enter for default): ").strip()
            course_id = int(course_id_input) if course_id_input else None
            
            import_to_database(df_with_predictions, course_id)
        
        print("\nTraining completed successfully!")