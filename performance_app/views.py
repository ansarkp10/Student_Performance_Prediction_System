from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.conf import settings
import pandas as pd
import json
import os
from datetime import datetime

from .forms import (
    UserRegistrationForm, UserLoginForm, CourseForm, 
    CSVUploadForm, StudentForm
)
from .models import UserProfile, Course, Student, UploadedFile, PredictionModel
from .ml_model import StudentPerformancePredictor
from .utils import generate_charts

# ===== HELPER FUNCTION =====
def get_or_create_user_profile(user):
    """Get user profile or create one if it doesn't exist"""
    try:
        return UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        # Create default UserProfile
        return UserProfile.objects.create(
            user=user,
            role='instructor',  # Default role
            institution='',
            phone=''
        )


@login_required
def dashboard(request):
    """Main dashboard view"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # Create a default UserProfile if it doesn't exist
        user_profile = UserProfile.objects.create(
            user=request.user,
            role='instructor',  # Default role
            institution='',
            phone=''
        )
        messages.info(request, 'Profile created with default settings.')
    
    # Get statistics
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        total_students = Student.objects.filter(course__in=courses).count()
        at_risk_students = Student.objects.filter(
            course__in=courses, 
            is_at_risk=True
        ).count()
        recent_students = Student.objects.filter(
            course__in=courses
        ).order_by('-created_at')[:5]
    else:
        courses = Course.objects.all()
        total_students = Student.objects.all().count()
        at_risk_students = Student.objects.filter(is_at_risk=True).count()
        recent_students = Student.objects.all().order_by('-created_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'total_courses': courses.count(),
        'total_students': total_students,
        'at_risk_students': at_risk_students,
        'recent_students': recent_students,
        'courses': courses,
    }
    
    return render(request, 'performance_app/dashboard.html', context)

def register_view(request):
    """User registration view - ONLY for students"""
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Create user
            user = form.save()
            
            # Create UserProfile with STUDENT role (always student)
            UserProfile.objects.create(
                user=user,
                role='student',  # ALWAYS 'student' for self-registration
                institution='',
                phone=form.cleaned_data.get('phone', '')
            )
            
            messages.success(request, 'Registration successful! Please login.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'performance_app/register.html', {'form': form})

def login_view(request):
    """User login view"""
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('dashboard')
    else:
        form = UserLoginForm()
    
    return render(request, 'performance_app/login.html', {'form': form})

@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required
def upload_csv(request):
    """CSV upload view"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user
            uploaded_file.save()
            
            try:
                # Process CSV file
                df = pd.read_csv(uploaded_file.file.path)
                
                # Validate required columns
                required_columns = ['student_id', 'first_name', 'last_name', 'email']
                if not all(col in df.columns for col in required_columns):
                    messages.error(request, 'CSV missing required columns.')
                    return redirect('upload_csv')
                
                # Process each row
                for _, row in df.iterrows():
                    student, created = Student.objects.update_or_create(
                        student_id=row['student_id'],
                        course=uploaded_file.course,
                        defaults={
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'email': row['email'],
                            'attendance': row.get('attendance', 100.0),
                            'assignment_score': row.get('assignment_score', 0.0),
                            'quiz_score': row.get('quiz_score', 0.0),
                            'time_spent': row.get('time_spent', 0.0),
                            'forum_posts': row.get('forum_posts', 0),
                            'resources_viewed': row.get('resources_viewed', 0),
                        }
                    )
                
                uploaded_file.processed = True
                uploaded_file.rows_processed = len(df)
                uploaded_file.save()
                
                messages.success(request, f'Successfully processed {len(df)} student records.')
                return redirect('students_list')
                
            except Exception as e:
                messages.error(request, f'Error processing CSV: {str(e)}')
    
    else:
        form = CSVUploadForm()
    
    context = {
        'form': form,
        'user_profile': user_profile,
    }
    return render(request, 'performance_app/upload_csv.html', context)

@login_required
def students_list(request):
    """Display list of students"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        students = Student.objects.filter(course__in=courses)
    else:
        students = Student.objects.all()
    
    # Filtering
    search_query = request.GET.get('search', '')
    performance_filter = request.GET.get('performance', '')
    
    if search_query:
        students = students.filter(
            Q(student_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if performance_filter:
        students = students.filter(predicted_performance=performance_filter)
    
    context = {
        'students': students,
        'user_profile': user_profile,
        'search_query': search_query,
        'performance_filter': performance_filter,
    }
    return render(request, 'performance_app/students_list.html', context)

@login_required
def predict_performance(request):
    """Predict performance for all students"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        algorithm = request.POST.get('algorithm', 'random_forest')
        
        # Get students data
        if user_profile.role == 'instructor':
            courses = Course.objects.filter(instructor=request.user)
            students = Student.objects.filter(course__in=courses)
        else:
            students = Student.objects.all()
        
        # Convert to DataFrame
        data = []
        for student in students:
            data.append({
                'student_id': student.student_id,
                'attendance': student.attendance,
                'assignment_score': student.assignment_score,
                'quiz_score': student.quiz_score,
                'time_spent': student.time_spent,
                'forum_posts': student.forum_posts,
                'resources_viewed': student.resources_viewed,
            })
        
        df = pd.DataFrame(data)
        
        # Train and predict
        predictor = StudentPerformancePredictor()
        metrics, features = predictor.train_model(df, algorithm)
        
        # Make predictions
        predictions = predictor.predict_batch(df)
        
        # Update students with predictions
        for pred in predictions:
            if pred['prediction'] != 'Error':
                student = Student.objects.get(student_id=pred['student_id'])
                student.predicted_performance = pred['prediction'].split(' ')[0].lower()
                student.is_at_risk = pred['is_at_risk']
                student.save()
        
        # Save model
        filename = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
        model_path = predictor.save_model(filename)
        
        # Save model record
        PredictionModel.objects.create(
            name=f"Model_{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            algorithm=algorithm,
            accuracy=metrics['accuracy'],
            precision=metrics['precision'],
            recall=metrics['recall'],
            model_file=str(model_path).replace(str(settings.MEDIA_ROOT) + '/', ''),
            features=features,
            is_active=True
        )
        
        messages.success(request, f'Predictions completed with accuracy: {metrics["accuracy"]:.2%}')
        return redirect('predictions_view')
    
    context = {
        'user_profile': user_profile,
        'algorithms': [
            ('random_forest', 'Random Forest'),
            ('decision_tree', 'Decision Tree'),
            ('logistic_regression', 'Logistic Regression'),
            ('svm', 'Support Vector Machine'),
            ('gradient_boosting', 'Gradient Boosting')
        ]
    }
    return render(request, 'performance_app/predict.html', context)

@login_required
def predictions_view(request):
    """View predictions"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        students = Student.objects.filter(course__in=courses)
    else:
        students = Student.objects.all()
    
    # Performance distribution
    performance_dist = {}
    for student in students:
        perf = student.predicted_performance or 'Not Predicted'
        performance_dist[perf] = performance_dist.get(perf, 0) + 1
    
    context = {
        'students': students,
        'user_profile': user_profile,
        'performance_dist': performance_dist,
        'total_students': students.count(),
        'at_risk_count': students.filter(is_at_risk=True).count(),
    }
    return render(request, 'performance_app/predictions.html', context)

# In views.py, ensure you have the right import
from .utils import generate_charts

@login_required
def visualize_data(request):
    """Data visualization dashboard"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        students = Student.objects.filter(course__in=courses)
    else:
        students = Student.objects.all()
    
    # Generate charts
    charts = generate_charts(students)
    
    context = {
        'user_profile': user_profile,
        'charts': charts,
        'total_students': students.count(),
    }
    return render(request, 'performance_app/visualize.html', context)

@login_required
def add_student(request):
    """Add individual student"""
    user_profile = get_or_create_user_profile(request.user)  # Use helper function
    
    if request.method == 'POST':
        form = StudentForm(request.POST, user=request.user)
        if form.is_valid():
            student = form.save()
            messages.success(request, f'Student {student.first_name} added successfully.')
            return redirect('students_list')
    else:
        form = StudentForm(user=request.user)
    
    context = {
        'form': form,
        'user_profile': user_profile,
        'has_courses': form.fields['course'].queryset.exists(),
    }
    return render(request, 'performance_app/add_student.html', context)

@login_required
def student_detail(request, student_id):
    """View student details"""
    student = get_object_or_404(Student, student_id=student_id)
    user_profile = UserProfile.objects.get(user=request.user)
    
    context = {
        'student': student,
        'user_profile': user_profile,
    }
    return render(request, 'performance_app/student_detail.html', context)

@login_required
def api_performance_distribution(request):
    """API for performance distribution chart"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        students = Student.objects.filter(course__in=courses)
    else:
        students = Student.objects.all()
    
    distribution = {
        'Excellent': students.filter(predicted_performance='excellent').count(),
        'Good': students.filter(predicted_performance='good').count(),
        'Average': students.filter(predicted_performance='average').count(),
        'Poor': students.filter(predicted_performance='poor').count(),
        'At Risk': students.filter(predicted_performance='at_risk').count(),
        'Not Predicted': students.filter(predicted_performance='').count(),
    }
    
    return JsonResponse(distribution)

@login_required
def add_course(request):
    """Add a new course"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.instructor = request.user
            course.save()
            messages.success(request, f'Course {course.course_name} created successfully.')
            return redirect('dashboard')
    else:
        form = CourseForm()
    
    context = {
        'form': form,
        'user_profile': user_profile,
    }
    return render(request, 'performance_app/add_course.html', context)

@login_required
def courses_list(request):
    """List all courses"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
    else:
        courses = Course.objects.all()
    
    context = {
        'courses': courses,
        'user_profile': user_profile,
    }
    return render(request, 'performance_app/courses_list.html', context)