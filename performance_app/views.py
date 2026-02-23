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
from .models import UserProfile, Course, Student, UploadedFile, PredictionModel, Instructor
from .ml_model import StudentPerformancePredictor
from .utils import generate_charts

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile, Student, Course
from .forms import AdminStudentRegistrationForm, AdminInstructorRegistrationForm
import random
import string
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count
from .models import Course, UserProfile
from django.db.models import Count

DEFAULT_PASSWORD = 'raheem@123'

# Check if user is admin
def is_admin(user):
    try:
        user_profile = UserProfile.objects.get(user=user)
        return user_profile.role == 'admin'
    except UserProfile.DoesNotExist:
        return False
    


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

def get_student_for_user(user):
    return Student.objects.filter(user_account=user).first()

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import UserProfile, Student, Course


@login_required
def dashboard(request):
    user_profile = UserProfile.objects.get(user=request.user)

    # ✅ SAFE student lookup
    student_obj = None
    if user_profile.role == 'student':
        student_obj = Student.objects.filter(user_account=request.user).first()

    # Instructor dashboard
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        total_students = Student.objects.filter(course__in=courses).count()
        at_risk_students = Student.objects.filter(
            course__in=courses, is_at_risk=True
        ).count()
        recent_students = Student.objects.filter(
            course__in=courses
        ).order_by('-created_at')[:5]

    # Admin dashboard
    elif user_profile.role == 'admin':
        courses = Course.objects.all()
        total_students = Student.objects.count()
        at_risk_students = Student.objects.filter(is_at_risk=True).count()
        recent_students = Student.objects.order_by('-created_at')[:5]

    # Student dashboard
    else:
        courses = Course.objects.filter(student__user_account=request.user)
        total_students = 1
        at_risk_students = Student.objects.filter(
            user_account=request.user, is_at_risk=True
        ).count()
        recent_students = []

    context = {
        'user_profile': user_profile,
        'student_obj': student_obj,   # ✅ IMPORTANT
        'total_courses': courses.count(),
        'total_students': total_students,
        'at_risk_students': at_risk_students,
        'recent_students': recent_students,
    }

    return render(request, 'performance_app/instructor/dashboard.html', context)


@login_required
def student_predictions_view(request):
    """
    Student can view ONLY their own prediction
    """
    user_profile = UserProfile.objects.get(user=request.user)

    # 🔒 Only students allowed
    if user_profile.role != 'student':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    # Get linked student
    student = Student.objects.filter(user_account=request.user).first()

    if not student:
        messages.error(request, "Student record not found.")
        return redirect('dashboard')

    context = {
        'user_profile': user_profile,
        'student': student,
        'predicted_performance': student.predicted_performance or "Not Predicted",
        'is_at_risk': student.is_at_risk,
        'confidence': 85,  # static for now (ML prob not stored)
    }

    return render(
        request,
        'performance_app/student/student_predictions.html',
        context
    )
    
def login_view(request):
    """User login view with role-based redirect"""

    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            return redirect(
                'admin_dashboard' if profile.role == 'admin' else 'dashboard'
            )
        except UserProfile.DoesNotExist:
            return redirect('dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = None

        # 🔹 Admin login (username fixed as 'admin')
        if identifier.lower() == 'admin':
            user = authenticate(request, username='admin', password=password)

        # 🔹 Instructor login (Instructor ID)
        if not user:
            try:
                instructor = Instructor.objects.get(instructor_id=identifier)
                if instructor.user_account:
                    user = authenticate(
                        request,
                        username=instructor.user_account.username,
                        password=password
                    )
            except Instructor.DoesNotExist:
                pass

        # 🔹 Student login (Student ID)
        if not user:
            try:
                student = Student.objects.get(student_id=identifier)
                if student.user_account:
                    user = authenticate(
                        request,
                        username=student.user_account.username,
                        password=password
                    )
            except Student.DoesNotExist:
                pass

        if user:
            login(request, user)

            try:
                profile = UserProfile.objects.get(user=user)

                if profile.role == 'admin':
                    messages.success(request, 'Welcome Admin!')
                    return redirect('admin_dashboard')

                messages.success(request, f'Welcome {user.first_name}!')
                return redirect('dashboard')

            except UserProfile.DoesNotExist:
                messages.error(request, 'User profile missing.')
                return redirect('dashboard')

        messages.error(request, 'Invalid credentials.')
        messages.info(request, 'Students: Student ID | Instructors: Instructor ID | Admin: admin')

    return render(request, 'performance_app/student/login.html')

@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    user_profile = UserProfile.objects.get(user=request.user)

    total_students = Student.objects.count()
    total_instructors = UserProfile.objects.filter(role='instructor').count()
    total_courses = Course.objects.count()
    total_users = User.objects.count()

    recent_students = Student.objects.order_by('-created_at')[:5]
    recent_users = User.objects.order_by('-date_joined')[:5]

    return render(
        request,
        'performance_app/admin/admin_dashboard.html',
        {
            'user_profile': user_profile,
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_courses': total_courses,
            'total_users': total_users,
            'recent_students': recent_students,
            'recent_users': recent_users,
        }
    )

@login_required
@user_passes_test(is_admin)
def admin_register_student(request):
    user_profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        form = AdminStudentRegistrationForm(request.POST)
        if form.is_valid():
            default_password = 'raheem@123'
            student_id = form.cleaned_data['student_id']

            base_username = f"stu_{student_id}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User.objects.create_user(
                username=username,
                email=form.cleaned_data['email'],
                password=default_password,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )

            UserProfile.objects.create(
                user=user,
                role='student',
                institution='',
                phone=form.cleaned_data.get('phone', '')
            )

            Student.objects.create(
                student_id=student_id,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                course=form.cleaned_data['course'],
                user_account=user
            )

            messages.success(request, 'Student registered successfully')
            return redirect('admin_students_list')
    else:
        form = AdminStudentRegistrationForm()

    return render(
        request,
        'performance_app/admin/admin_register_student.html',
        {
            'form': form,
            'user_profile': user_profile,
        }
    )

@login_required
@user_passes_test(is_admin)
def admin_register_instructor(request):
    user_profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        form = AdminInstructorRegistrationForm(request.POST)
        if form.is_valid():
            default_password = 'raheem@123'
            instructor_id = form.cleaned_data['instructor_id']

            # Create username from instructor_id
            base_username = f"ins_{instructor_id}"
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

            # Create User account
            user = User.objects.create_user(
                username=username,
                email=form.cleaned_data['email'],
                password=default_password,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )

            # Create UserProfile
            UserProfile.objects.create(
                user=user,
                role='instructor',
                institution=form.cleaned_data['institution'],
                phone=form.cleaned_data.get('phone', '')
            )

            # Create Instructor record
            instructor = Instructor.objects.create(
                instructor_id=instructor_id,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                institution=form.cleaned_data['institution'],
                phone=form.cleaned_data.get('phone', ''),
                user_account=user
            )

            # Assign course if selected
            course = form.cleaned_data.get('course')
            if course:
                course.instructor = user
                course.save()

            messages.success(request, f'✅ Instructor {instructor_id} registered successfully!')
            messages.info(request, f'📋 Login Instructions:')
            messages.info(request, f'   Instructor ID: <strong>{instructor_id}</strong>')
            messages.info(request, f'   Password: <strong>{default_password}</strong>')
            messages.info(request, f'   (Instructor must login using Instructor ID, not username)')
            
            return redirect('admin_instructors_list')
    else:
        form = AdminInstructorRegistrationForm()

    return render(
        request,
        'performance_app/admin/admin_register_instructor.html',
        {
            'form': form,
            'user_profile': user_profile,
        }
    )

@login_required
@user_passes_test(is_admin)
def admin_delete_instructor_direct(request, user_id):
    """Delete instructor directly - NO CONFIRMATION, NO ALERT"""
    try:
        user = User.objects.get(id=user_id)
        
        # Delete instructor record first
        try:
            instructor = Instructor.objects.get(user_account=user)
            instructor_id = instructor.instructor_id
            instructor.delete()
        except Instructor.DoesNotExist:
            instructor_id = 'Unknown'
        
        # Delete user profile
        try:
            profile = UserProfile.objects.get(user=user)
            profile.delete()
        except UserProfile.DoesNotExist:
            pass
        
        # Delete user
        user.delete()
        
        # Optional: Add a success message (remove if you want no notification)
        messages.success(request, f'✅ Instructor deleted successfully.')
        
    except User.DoesNotExist:
        messages.error(request, '❌ User not found.')
    
    return redirect('admin_instructors_list')

@login_required
@user_passes_test(is_admin)
def admin_delete_student_direct(request, student_id):
    """Delete student directly - NO CONFIRMATION, NO ALERT"""
    student = get_object_or_404(Student, student_id=student_id)
    
    # Delete user account if exists
    if student.user_account:
        student.user_account.delete()
    
    student.delete()
    
    # Optional: Add a success message (remove if you want no notification)
    messages.success(request, f'✅ Student deleted successfully.')
    
    return redirect('admin_students_list')
    
@login_required
@user_passes_test(is_admin)
def admin_students_list(request):
    user_profile = UserProfile.objects.get(user=request.user)
    students = Student.objects.select_related('user_account', 'course')

    return render(
        request,
        'performance_app/admin/admin_students_list.html',
        {
            'students': students,
            'user_profile': user_profile,
        }
    )

@login_required
@user_passes_test(is_admin)
def admin_instructors_list(request):
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Use Instructor model instead of UserProfile
    instructors = Instructor.objects.select_related('user_account').all().order_by('-created_at')
    
    # Calculate statistics
    total_instructors = instructors.count()
    total_courses = Course.objects.filter(instructor__in=[i.user_account for i in instructors if i.user_account]).count()
    recent_count = instructors.filter(created_at__gte=timezone.now() - timezone.timedelta(days=30)).count()
    
    return render(
        request,
        'performance_app/admin/admin_instructors_list.html',
        {
            'instructors': instructors,
            'user_profile': user_profile,
            'total_courses': total_courses,
            'recent_count': recent_count,
        }
    )

@login_required
@user_passes_test(is_admin)
def reset_password(request, user_id):
    """Reset user password to default"""
    user = get_object_or_404(User, id=user_id)
    default_password = 'raheem@123'
    
    user.set_password(default_password)
    user.save()
    
    messages.success(request, f'Password for {user.username} has been reset to default: {default_password}')
    return redirect(request.META.get('HTTP_REFERER', 'admin_dashboard'))


@login_required
def upload_csv(request):
    user_profile = UserProfile.objects.get(user=request.user)

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user
            uploaded_file.save()

            try:
                df = pd.read_csv(uploaded_file.file.path)

                # REQUIRED columns
                required_columns = ['student_id', 'first_name', 'last_name', 'email']
                for col in required_columns:
                    if col not in df.columns:
                        messages.error(request, f"Missing column: {col}")
                        return redirect('upload_csv')

                course = uploaded_file.course

                for _, row in df.iterrows():
                    student_id = str(row['student_id']).strip()
                    first_name = row['first_name']
                    last_name = row['last_name']
                    email = row['email']

                    # ===============================
                    # 1️⃣ CREATE USER ACCOUNT
                    # ===============================
                    username = f"stu_{student_id}"

                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                        }
                    )

                    if created:
                        user.set_password(DEFAULT_PASSWORD)
                        user.save()

                        # Create UserProfile
                        UserProfile.objects.create(
                            user=user,
                            role='student',
                            institution='',
                            phone=''
                        )

                    # ===============================
                    # 2️⃣ CREATE / UPDATE STUDENT
                    # ===============================
                    Student.objects.update_or_create(
                        student_id=student_id,
                        course=course,
                        defaults={
                            'first_name': first_name,
                            'last_name': last_name,
                            'email': email,
                            'attendance': row.get('attendance', 100.0),
                            'assignment_score': row.get('assignment_score', 0.0),
                            'quiz_score': row.get('quiz_score', 0.0),
                            'time_spent': row.get('time_spent', 0.0),
                            'forum_posts': row.get('forum_posts', 0),
                            'resources_viewed': row.get('resources_viewed', 0),
                            'user_account': user,   # 🔥 THIS FIXES LOGIN
                        }
                    )

                uploaded_file.processed = True
                uploaded_file.rows_processed = len(df)
                uploaded_file.save()

                messages.success(
                    request,
                    f"✅ {len(df)} students uploaded successfully.\n"
                    f"Login Password for all students: {DEFAULT_PASSWORD}"
                )

                return redirect('admin_students_list')

            except Exception as e:
                messages.error(request, f"CSV processing error: {str(e)}")
                return redirect('upload_csv')

    else:
        form = CSVUploadForm()

    return render(request, 'performance_app/admin/upload_csv.html', {
        'form': form,
        'user_profile': user_profile
    })

@login_required
def students_list(request):
    """Display list of students"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get all students based on user role
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
        students = Student.objects.filter(course__in=courses)
    else:
        students = Student.objects.all()
    
    # Filter by course if course_id is provided in query parameters
    course_id = request.GET.get('course')
    if course_id:
        try:
            course = Course.objects.get(id=course_id)
            # Verify user has access to this course
            if user_profile.role == 'instructor' and course.instructor != request.user:
                messages.error(request, 'You do not have access to this course.')
                return redirect('students_list')
            
            students = students.filter(course=course)
            selected_course = course
        except (Course.DoesNotExist, ValueError):
            selected_course = None
            messages.warning(request, 'Invalid course selected.')
    else:
        selected_course = None
    
    # Additional filtering by search query and performance
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
        'selected_course': selected_course,
        'courses': Course.objects.all() if user_profile.role != 'instructor' 
                  else Course.objects.filter(instructor=request.user),
    }
    return render(request, 'performance_app/student/students_list.html', context)

@login_required
def predict_performance(request):
    """Predict performance for students in a specific course"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        course_id = request.POST.get('course')
        
        if not course_id:
            messages.error(request, 'Please select a course.')
            return redirect('predict_performance')
        
        try:
            course = Course.objects.get(id=course_id)
            
            # Verify user has access to this course
            if user_profile.role == 'instructor' and course.instructor != request.user:
                messages.error(request, 'You do not have access to this course.')
                return redirect('predict_performance')
            
            # Get students for this course
            students = Student.objects.filter(course=course)
            
            if not students.exists():
                messages.error(request, 'No students found in this course.')
                return redirect('predict_performance')
            
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
            
            # Train and predict (using default Random Forest)
            predictor = StudentPerformancePredictor()
            metrics, features = predictor.train_model(df, 'random_forest')
            
            # Make predictions
            predictions = predictor.predict_batch(df)
            
            # Update students with predictions
            updated_count = 0
            for pred in predictions:
                if pred['prediction'] != 'Error':
                    try:
                        student = Student.objects.get(
                            student_id=pred['student_id'],
                            course=course
                        )
                        student.predicted_performance = pred['prediction'].split(' ')[0].lower()
                        student.is_at_risk = pred['is_at_risk']
                        student.save()
                        updated_count += 1
                    except Student.DoesNotExist:
                        continue
            
            messages.success(
                request, 
                f'Predictions completed for {updated_count} students in {course.course_name}. '
                f'Accuracy: {metrics["accuracy"]:.1%}'
            )
            return redirect('predictions_view')
            
        except Course.DoesNotExist:
            messages.error(request, 'Course not found.')
            return redirect('predict_performance')
    
    # GET request - show form
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
    else:
        courses = Course.objects.all()
    
    context = {
        'user_profile': user_profile,
        'courses': courses,
    }
    return render(request, 'performance_app/instructor/predict.html', context)

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
    return render(request, 'performance_app/instructor/predictions.html', context)

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
    return render(request, 'performance_app/student/visualize.html', context)

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
    return render(request, 'performance_app/admin/add_student.html', context)

@login_required
def student_detail(request, student_id):
    """View student details"""
    student = get_object_or_404(Student, student_id=student_id)
    user_profile = UserProfile.objects.get(user=request.user)
    
    context = {
        'student': student,
        'user_profile': user_profile,
    }
    return render(request, 'performance_app/student/student_detail.html', context)

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
    return render(request, 'performance_app/admin/add_course.html', context)


@login_required
def courses_list(request):
    user_profile = UserProfile.objects.get(user=request.user)
    today = timezone.now().date()

    # Role-based course access
    if user_profile.role == 'instructor':
        courses = Course.objects.filter(instructor=request.user)
    else:
        courses = Course.objects.all()

    # Annotate with student count
    courses = courses.annotate(
        student_count=Count('student')
    ).select_related('instructor')

    # Calculate statistics for admin
    statistics = {}
    if user_profile.role == 'admin':
        # Active courses
        active_courses = courses.filter(
            start_date__lte=today,
            end_date__gte=today
        ).count()

        # Total courses
        total_courses = courses.count()

        # Total students across all courses
        total_students = Student.objects.count()

        # Unique instructors
        unique_instructors = courses.values('instructor').distinct().count()

        statistics = {
            'total_courses': total_courses,
            'active_courses': active_courses,
            'total_students': total_students,
            'unique_instructors': unique_instructors,
        }

    # Calculate instructor-specific stats
    total_students_count = 0
    at_risk_count = 0
    
    if user_profile.role == 'instructor':
        for course in courses:
            students = Student.objects.filter(course=course)
            total_students_count += students.count()
            at_risk_count += students.filter(is_at_risk=True).count()

    context = {
        'courses': courses,
        'user_profile': user_profile,
        'statistics': statistics,
        'total_students_count': total_students_count,
        'at_risk_count': at_risk_count,
    }

    return render(request, 'performance_app/student/courses_list.html', context)

@login_required
def student_courses_view(request):
    user_profile = UserProfile.objects.get(user=request.user)

    # 🔒 Only students allowed
    if user_profile.role != 'student':
        messages.error(request, "Access denied.")
        return redirect('dashboard')

    # Get student linked to logged-in user
    student = Student.objects.filter(user_account=request.user).select_related('course').first()

    if not student or not student.course:
        messages.warning(request, "No course assigned.")
        courses = []
    else:
        courses = [student.course]  # list for template consistency

    today = timezone.now().date()

    course_data = []
    for course in courses:
        # Determine course status
        if course.start_date and course.end_date:
            if course.start_date <= today <= course.end_date:
                status = "Active"
            elif today > course.end_date:
                status = "Completed"
            else:
                status = "Upcoming"
        else:
            status = "Active"

        course_data.append({
            'course_name': course.course_name,
            'instructor': course.instructor.get_full_name() if course.instructor else "Not Assigned",
            'start_date': course.start_date,
            'end_date': course.end_date,
            'status': status
        })

    context = {
        'user_profile': user_profile,
        'student': student,
        'courses': course_data
    }

    return render(request, 'performance_app/student/student_courses.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Course, UserProfile


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user_profile = UserProfile.objects.get(user=request.user)

    return render(request, 'performance_app/student/course_detail.html', {
        'course': course,
        'user_profile': user_profile
    })


@login_required
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Temporary placeholder page
    return render(request, 'performance_app/student/edit_course.html', {
        'course': course
    })



@login_required
@user_passes_test(is_admin)
def admin_delete_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)

    if request.method == "POST":
        # Optional: also delete linked user account
        if student.user_account:
            student.user_account.delete()

        student.delete()
        messages.success(request, "Student deleted successfully.")
        return redirect('admin_students_list')

    # If someone tries GET, just redirect
    return redirect('admin_students_list')

@login_required
def train_model_view(request):
    """Train model with uploaded CSV"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        # Handle CSV upload and training
        form = CSVUploadForm(request.POST, request.FILES)
        
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user
            uploaded_file.save()
            
            try:
                # Process CSV
                df = pd.read_csv(uploaded_file.file.path)
                
                # Get algorithm
                algorithm = request.POST.get('algorithm', 'random_forest')
                
                # Train model
                predictor = StudentPerformancePredictor()
                metrics, features = predictor.train_model(df, algorithm)
                
                # Save model
                filename = f"trained_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
                model_path = predictor.save_model(filename)
                
                # Create model record
                model_record = PredictionModel.objects.create(
                    name=f"Trained Model {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    algorithm=algorithm,
                    accuracy=metrics['accuracy'],
                    precision=metrics['precision'],
                    recall=metrics['recall'],
                    model_file=str(model_path).replace(str(settings.MEDIA_ROOT) + '/', ''),
                    features=json.dumps(features),
                    is_active=True,
                    trained_by=request.user
                )
                
                messages.success(
                    request, 
                    f'Model trained successfully! Accuracy: {metrics["accuracy"]:.2%}'
                )
                return redirect('models_list')
                
            except Exception as e:
                messages.error(request, f'Error training model: {str(e)}')
    
    else:
        form = CSVUploadForm()
    
    context = {
        'form': form,
        'user_profile': user_profile,
        'algorithms': [
            ('random_forest', 'Random Forest'),
            ('decision_tree', 'Decision Tree'),
            ('logistic_regression', 'Logistic Regression'),
            ('svm', 'Support Vector Machine'),
            ('gradient_boosting', 'Gradient Boosting')
        ]
    }
    return render(request, 'performance_app/train_model.html', context)