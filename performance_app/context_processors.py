from .models import Student

def global_student_context(request):
    """
    Makes student_obj available in ALL templates
    """
    if request.user.is_authenticated:
        student = Student.objects.filter(user_account=request.user).first()
        return {
            'student_obj': student
        }
    return {
        'student_obj': None
    }