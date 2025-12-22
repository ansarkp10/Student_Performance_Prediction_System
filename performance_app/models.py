from django.db import models
from django.contrib.auth.models import User
import uuid

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='instructor')
    institution = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Course(models.Model):
    course_id = models.CharField(max_length=20, unique=True)
    course_name = models.CharField(max_length=200)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='courses')
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.course_id} - {self.course_name}"
    
    class Meta:
        ordering = ['-created_at']

class Student(models.Model):
    PERFORMANCE_CHOICES = [
        ('excellent', 'Excellent (A)'),
        ('good', 'Good (B)'),
        ('average', 'Average (C)'),
        ('poor', 'Poor (D)'),
        ('at_risk', 'At Risk (F)'),
    ]
    
    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='students')
    attendance = models.FloatField(default=100.0)  # percentage
    assignment_score = models.FloatField(default=0.0)
    quiz_score = models.FloatField(default=0.0)
    time_spent = models.FloatField(default=0.0)  # hours
    forum_posts = models.IntegerField(default=0)
    resources_viewed = models.IntegerField(default=0)
    predicted_performance = models.CharField(max_length=20, choices=PERFORMANCE_CHOICES, blank=True)
    actual_performance = models.CharField(max_length=20, choices=PERFORMANCE_CHOICES, blank=True)
    is_at_risk = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class UploadedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to='uploads/csv/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    rows_processed = models.IntegerField(default=0)

class PredictionModel(models.Model):
    name = models.CharField(max_length=100)
    algorithm = models.CharField(max_length=50)
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    model_file = models.FileField(upload_to='models/', null=True, blank=True)
    features = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)