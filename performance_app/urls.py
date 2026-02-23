# performance_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main views
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_csv, name='upload_csv'),
    path('students/', views.students_list, name='students_list'),
    path('student/add/', views.add_student, name='add_student'),
    path('student/<str:student_id>/', views.student_detail, name='student_detail'),
    path('my-predictions/', views.student_predictions_view, name='student_predictions'),
    path('my-courses/', views.student_courses_view, name='student_courses'),
    
    # Course management
    path('courses/', views.courses_list, name='courses_list'),
    path('course/add/', views.add_course, name='add_course'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    # path('course/<int:course_id>/delete/', views.delete_course, name='delete_course'),
    
    # Prediction
    path('predict/', views.predict_performance, name='predict_performance'),
    path('predictions/', views.predictions_view, name='predictions_view'),
    
    # Visualization
    path('visualize/', views.visualize_data, name='visualize_data'),
    path('api/performance-distribution/', views.api_performance_distribution, name='api_performance_distribution'),

    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin_register_student/', views.admin_register_student, name='admin_register_student'),
    path('admin_register_instructor/', views.admin_register_instructor, name='admin_register_instructor'),
    path('admin_students_list/', views.admin_students_list, name='admin_students_list'),
    path('admin_instructors_list/', views.admin_instructors_list, name='admin_instructors_list'),
    path('admin/reset-password/<int:user_id>/', views.reset_password, name='reset_password'),
    path('manage/student/delete/<str:student_id>/', views.admin_delete_student, name='admin_delete_student'),

    path('admin/delete-instructor/<int:user_id>/', views.admin_delete_instructor_direct, name='admin_delete_instructor_direct'),
]