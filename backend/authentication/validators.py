from django.core.exceptions import ValidationError


class CustomPasswordValidator:
    """
    Custom password validator enforcing:
    - Length between 8-16 characters
    - At least one number (0-9)
    - At least one uppercase letter (A-Z)
    """
    
    def validate(self, password, user=None):
        # Check length (8-16 characters)
        if len(password) < 8 or len(password) > 16:
            raise ValidationError(
                'Password must be between 8 and 16 characters.',
                code='password_length'
            )
        
        # Check for at least one digit
        if not any(char.isdigit() for char in password):
            raise ValidationError(
                'Password must contain at least one number.',
                code='password_no_number'
            )
        
        # Check for at least one uppercase letter
        if not any(char.isupper() for char in password):
            raise ValidationError(
                'Password must contain at least one uppercase letter.',
                code='password_no_uppercase'
            )
    
    def get_help_text(self):
        return (
            'Your password must be between 8 and 16 characters long, '
            'contain at least one number, and at least one uppercase letter.'
        )
