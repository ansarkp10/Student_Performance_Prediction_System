from django.contrib import admin
from .models import UserProfile, Course, Student, UploadedFile, PredictionModel

# Register your models here.

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'institution', 'phone', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__username', 'institution']

class CourseAdmin(admin.ModelAdmin):
    list_display = ['course_id', 'course_name', 'instructor', 'start_date', 'end_date', 'created_at']
    list_filter = ['start_date', 'end_date']
    search_fields = ['course_id', 'course_name', 'instructor__username']
    raw_id_fields = ['instructor']

class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'first_name', 'last_name', 'course', 'attendance', 'assignment_score', 
                    'quiz_score', 'predicted_performance', 'is_at_risk', 'created_at']
    list_filter = ['predicted_performance', 'is_at_risk', 'course', 'created_at']
    search_fields = ['student_id', 'first_name', 'last_name', 'email']
    list_editable = ['attendance', 'assignment_score', 'quiz_score']
    readonly_fields = ['created_at', 'updated_at']

class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'course', 'uploaded_at', 'processed', 'rows_processed']
    list_filter = ['processed', 'uploaded_at']
    search_fields = ['user__username', 'course__course_name']

class PredictionModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'algorithm', 'accuracy', 'created_at', 'is_active']
    list_filter = ['algorithm', 'is_active', 'created_at']
    search_fields = ['name', 'algorithm']

# Register models
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(UploadedFile, UploadedFileAdmin)
admin.site.register(PredictionModel, PredictionModelAdmin)