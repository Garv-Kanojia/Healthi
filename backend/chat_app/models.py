from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
import base64
import json


class Chat(models.Model):
    """
    Chat model representing individual chat sessions for users.
    Each user can have a maximum of 3 chats.
    """
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chats'
    )
    
    # Chat identification
    chat_id = models.TextField(
        unique=True,
        db_index=True,
        help_text="Unique chat identifier used for vector search (created_at timestamp)"
    )
    
    # Chat metadata
    name = models.CharField(
        max_length=255,
        default="Chat",
        help_text="User-defined chat name, can be changed anytime"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Chat creation timestamp, also used as chat_id for vector search"
    )
    
    class Meta:
        db_table = 'chats'
        verbose_name = 'Chat'
        verbose_name_plural = 'Chats'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['chat_id']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.name} ({self.chat_id})"
    
    def save(self, *args, **kwargs):
        """
        Override save to set chat_id from created_at timestamp on first save.
        """
        if not self.pk and not self.chat_id:
            # For new chats, set chat_id based on timestamp
            from django.utils import timezone
            self.chat_id = str(timezone.now().timestamp())
        
        self.full_clean()
        super().save(*args, **kwargs)


class Message(models.Model):
    """
    Message model storing prompt-response pairs for each chat.
    Content is stored as encrypted JSON with format: {"prompt": "...", "response": "..."}
    where both prompt and response are pre-encrypted before being combined in JSON.
    """
    
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    
    # Message content (encrypted JSON with prompt-response pair)
    content = models.TextField(
        help_text='Encrypted message content stored as JSON: {"prompt": "...", "response": "..."}'
    )
    
    # Message sequence number
    count = models.IntegerField(
        help_text="Message sequence number in the specific chat"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['count']
        unique_together = ['chat', 'count']
        indexes = [
            models.Index(fields=['chat', 'count']),
            models.Index(fields=['chat', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.chat.name} - Message #{self.count}"
    
    @staticmethod
    def get_encryption_key():
        """
        Get or generate encryption key for message content.
        In production, this should be stored securely (e.g., in environment variables).
        """
        from django.conf import settings
        key = getattr(settings, 'MESSAGE_ENCRYPTION_KEY', None)
        if not key:
            # Generate a new key if not exists (for development only)
            key = Fernet.generate_key()
        elif isinstance(key, str):
            key = key.encode()
        return key
    
    def encrypt_text(self, text):
        """
        Encrypt individual text (prompt or response) before storing.
        
        Args:
            text (str): Text to encrypt
        
        Returns:
            str: Encrypted text as base64 string
        """
        fernet = Fernet(self.get_encryption_key())
        encrypted = fernet.encrypt(text.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_text(self, encrypted_text):
        """
        Decrypt individual text (prompt or response) for retrieval.
        
        Args:
            encrypted_text (str): Encrypted text as base64 string
        
        Returns:
            str: Decrypted text
        """
        try:
            fernet = Fernet(self.get_encryption_key())
            encrypted_bytes = base64.b64decode(encrypted_text.encode())
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            return f"Decryption failed: {str(e)}"
    
    def set_content(self, prompt, response):
        """
        Set and encrypt message content.
        Encrypts prompt and response individually, then stores as JSON.
        
        Args:
            prompt (str): User prompt text
            response (str): Assistant response text
        """
        encrypted_prompt = self.encrypt_text(prompt)
        encrypted_response = self.encrypt_text(response)
        
        content_dict = {
            "prompt": encrypted_prompt,
            "response": encrypted_response
        }
        self.content = json.dumps(content_dict)
    
    def get_content(self):
        """
        Get and decrypt message content.
        
        Returns:
            dict: Dictionary with decrypted prompt and response
                  {"prompt": "...", "response": "..."}
        """
        try:
            content_dict = json.loads(self.content)
            decrypted_prompt = self.decrypt_text(content_dict.get("prompt", ""))
            decrypted_response = self.decrypt_text(content_dict.get("response", ""))
            
            return {
                "prompt": decrypted_prompt,
                "response": decrypted_response
            }
        except Exception as e:
            return {"error": f"Content retrieval failed: {str(e)}"}


class MessageFile(models.Model):
    """
    Model for storing file metadata associated with messages.
    Stores only file names and metadata; actual file data is sent to microservice for processing.
    """
    
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('pdf', 'PDF'),
    ]
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='files'
    )
    
    # File metadata
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        help_text="Type of file: image or pdf"
    )
    
    file_name = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes"
    )
    
    class Meta:
        db_table = 'message_files'
        verbose_name = 'Message File'
        verbose_name_plural = 'Message Files'
        ordering = ['id']
        indexes = [
            models.Index(fields=['message']),
        ]
    
    def __str__(self):
        return f"{self.file_name} ({self.file_type}) - Message #{self.message.count}"
    
    def clean(self):
        """
        Validate file constraints.
        """
        # Check number of files per message
        if not self.pk:  # Only check for new files
            message_files = MessageFile.objects.filter(message=self.message)
            
            if self.file_type == 'image':
                image_count = message_files.filter(file_type='image').count()
                if image_count >= 5:
                    raise ValidationError(
                        "A message can have a maximum of 5 images."
                    )
                # Validate image size (10MB max)
                if self.file_size > 10 * 1024 * 1024:
                    raise ValidationError(
                        "Image file size cannot exceed 10MB."
                    )
            
            elif self.file_type == 'pdf':
                pdf_count = message_files.filter(file_type='pdf').count()
                if pdf_count >= 2:
                    raise ValidationError(
                        "A message can have a maximum of 2 PDFs."
                    )
                # Validate PDF size (25MB max)
                if self.file_size > 25 * 1024 * 1024:
                    raise ValidationError(
                        "PDF file size cannot exceed 25MB."
                    )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)