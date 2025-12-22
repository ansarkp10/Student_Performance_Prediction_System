from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_csv, name='upload_csv'),
    path('students/', views.students_list, name='students_list'),
    path('student/add/', views.add_student, name='add_student'),
    path('student/<str:student_id>/', views.student_detail, name='student_detail'),
    
    # Course management
    path('courses/', views.courses_list, name='courses_list'),
    path('course/add/', views.add_course, name='add_course'),
    
    # Prediction
    path('predict/', views.predict_performance, name='predict_performance'),
    path('predictions/', views.predictions_view, name='predictions_view'),
    
    # Visualization
    path('visualize/', views.visualize_data, name='visualize_data'),
    path('api/performance-distribution/', views.api_performance_distribution, name='api_performance_distribution'),
]