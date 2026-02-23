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
    
    # Add role field with choices (excluding admin for self-registration)
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('instructor', 'Instructor'),
    ]
    
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        initial='student',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Conditional fields - only show student_id for students
    student_id = forms.CharField(
        max_length=20,
        required=False,  # Not required for instructors
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student ID'}),
        help_text="Required for students only"
    )
    
    # Add instructor-specific field
    institution = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Institution/University (for instructors)'})
    )
    
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone (optional)'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 
                 'student_id', 'institution', 'phone', 'password1', 'password2']
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
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        student_id = cleaned_data.get('student_id')
        
        # Validate that students have a student_id
        if role == 'student' and not student_id:
            self.add_error('student_id', 'Student ID is required for students')
        
        # Validate that instructors have an institution
        if role == 'instructor':
            institution = cleaned_data.get('institution')
            if not institution:
                self.add_error('institution', 'Institution is required for instructors')
        
        return cleaned_data
        
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

class AdminStudentRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, widget=forms.TextInput(attrs={'class': 'form-control'}))
    student_id = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-control'}))
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists')
        return username
    
    def clean_student_id(self):
        student_id = self.cleaned_data['student_id']
        if Student.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError('Student ID already exists')
        return student_id

class AdminInstructorRegistrationForm(forms.Form):
    instructor_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., INS001',
            'style': 'text-transform: uppercase;'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'instructor@university.edu'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    institution = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., University of Technology'
        })
    )
    phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., +1 234 567 8900'
        })
    )
    
    # Optional course field
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="-- Select Course (Optional) --"
    )
    
    def clean_instructor_id(self):
        instructor_id = self.cleaned_data['instructor_id'].strip().upper()
        
        # Remove special characters
        instructor_id = ''.join(c for c in instructor_id if c.isalnum())
        
        if not instructor_id:
            raise forms.ValidationError('Instructor ID is required')
            
        # Check if instructor ID already exists in Instructor model
        from .models import Instructor
        if Instructor.objects.filter(instructor_id=instructor_id).exists():
            raise forms.ValidationError(f'Instructor ID "{instructor_id}" already exists')
        
        return instructor_id
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered')
        return email