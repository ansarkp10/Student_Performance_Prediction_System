from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile, Course, Student, UploadedFile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'})
    )
    student_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student ID'})
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone (optional)'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'student_id', 'phone', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove help text
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        self.fields['username'].help_text = ''
        
        # Add placeholders
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
        
        # Set labels
        self.fields['student_id'].label = 'Student ID'

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_id', 'course_name', 'description', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class CSVUploadForm(forms.ModelForm):
    course = forms.ModelChoiceField(queryset=Course.objects.all(), required=True)
    
    class Meta:
        model = UploadedFile
        fields = ['course', 'file']
        widgets = {
            'file': forms.FileInput(attrs={'accept': '.csv'})
        }

class StudentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # Extract user parameter
        super(StudentForm, self).__init__(*args, **kwargs)
        
        # Filter courses based on user role
        if self.user:
            try:
                user_profile = UserProfile.objects.get(user=self.user)
                if user_profile.role == 'instructor':
                    self.fields['course'].queryset = Course.objects.filter(instructor=self.user)
                else:
                    self.fields['course'].queryset = Course.objects.all()
            except UserProfile.DoesNotExist:
                self.fields['course'].queryset = Course.objects.all()
        else:
            self.fields['course'].queryset = Course.objects.all()
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),  # Will be populated in __init__
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Course --"
    )
    
    class Meta:
        model = Student
        fields = ['student_id', 'first_name', 'last_name', 'email', 'course',
                 'attendance', 'assignment_score', 'quiz_score', 'time_spent', 
                 'forum_posts', 'resources_viewed', 'actual_performance', 'notes']
        widgets = {
            'attendance': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '100'}),
            'assignment_score': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '100'}),
            'quiz_score': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '100'}),
            'time_spent': forms.NumberInput(attrs={'step': '0.1', 'min': '0'}),
        }
        
class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_id', 'course_name', 'description', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'course_id': 'Course Code',
            'course_name': 'Course Name',
        }