from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from chat_app.models import Chat, Message, MessageFile
import json

User = get_user_model()

class ChatModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            name='Test User'
        )

    def test_create_chat(self):
        chat = Chat.objects.create(user=self.user, name="Test Chat")
        self.assertEqual(chat.user, self.user)
        self.assertEqual(chat.name, "Test Chat")
        self.assertIsNotNone(chat.chat_id)
        self.assertIsNotNone(chat.created_at)

    def test_chat_limit_constraint(self):
        # Create 3 chats
        for i in range(3):
            Chat.objects.create(user=self.user, name=f"Chat {i}")
        
        # Try to create 4th chat
        with self.assertRaises(ValidationError):
            Chat.objects.create(user=self.user, name="Chat 4")

    def test_chat_str_representation(self):
        chat = Chat.objects.create(user=self.user, name="Test Chat")
        expected_str = f"{self.user.email} - {chat.name} ({chat.chat_id})"
        self.assertEqual(str(chat), expected_str)

class MessageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            name='Test User'
        )
        self.chat = Chat.objects.create(user=self.user, name="Test Chat")

    def test_create_message_encryption(self):
        message = Message(chat=self.chat)
        prompt = "Hello AI"
        response = "Hello User"
        
        message.set_content(prompt, response)
        message.save()
        
        # Check that content is stored as JSON and encrypted
        self.assertNotEqual(message.content, prompt)
        self.assertNotEqual(message.content, response)
        
        content_json = json.loads(message.content)
        self.assertIn("prompt", content_json)
        self.assertIn("response", content_json)
        
        # Verify decryption
        decrypted = message.get_content()
        self.assertEqual(decrypted["prompt"], prompt)
        self.assertEqual(decrypted["response"], response)

    def test_message_str_representation(self):
        message = Message.objects.create(chat=self.chat, content="{}")
        expected_str = f"{self.chat.name} - {message.created_at}"
        self.assertEqual(str(message), expected_str)

class MessageFileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            name='Test User'
        )
        self.chat = Chat.objects.create(user=self.user, name="Test Chat")
        self.message = Message.objects.create(chat=self.chat, content="{}")

    def test_create_image_file(self):
        file = MessageFile.objects.create(
            message=self.message,
            file_type='image',
            file_name='test.jpg',
            file_size=1024
        )
        self.assertEqual(file.file_type, 'image')
        self.assertEqual(file.file_size, 1024)

    def test_image_limit_constraint(self):
        # Create 5 images
        for i in range(5):
            MessageFile.objects.create(
                message=self.message,
                file_type='image',
                file_name=f'img{i}.jpg',
                file_size=100
            )
        
        # Try to create 6th image
        with self.assertRaises(ValidationError):
            MessageFile.objects.create(
                message=self.message,
                file_type='image',
                file_name='img6.jpg',
                file_size=100
            )

    def test_pdf_limit_constraint(self):
        # Create 2 PDFs
        for i in range(2):
            MessageFile.objects.create(
                message=self.message,
                file_type='pdf',
                file_name=f'doc{i}.pdf',
                file_size=100
            )
        
        # Try to create 3rd PDF
        with self.assertRaises(ValidationError):
            MessageFile.objects.create(
                message=self.message,
                file_type='pdf',
                file_name='doc3.pdf',
                file_size=100
            )

    def test_image_size_limit(self):
        # 10MB + 1 byte
        large_size = 10 * 1024 * 1024 + 1
        with self.assertRaises(ValidationError):
            MessageFile.objects.create(
                message=self.message,
                file_type='image',
                file_name='large.jpg',
                file_size=large_size
            )

    def test_pdf_size_limit(self):
        # 25MB + 1 byte
        large_size = 25 * 1024 * 1024 + 1
        with self.assertRaises(ValidationError):
            MessageFile.objects.create(
                message=self.message,
                file_type='pdf',
                file_name='large.pdf',
                file_size=large_size
            )
