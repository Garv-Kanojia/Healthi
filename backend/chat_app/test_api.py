from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from chat_app.models import Chat, Message
from unittest.mock import patch, MagicMock

User = get_user_model()

class ChatListCreateAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            name='Test User'
        )
        self.client.force_authenticate(user=self.user)
        self.url = reverse('chat-list-create')

    def test_create_chat(self):
        data = {'name': 'New Chat'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Chat.objects.count(), 1)
        self.assertEqual(Chat.objects.first().name, 'New Chat')

    def test_list_chats(self):
        Chat.objects.create(user=self.user, name="Chat 1")
        Chat.objects.create(user=self.user, name="Chat 2")
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['chats']), 2)

    def test_create_chat_limit(self):
        # Create 3 chats
        for i in range(3):
            Chat.objects.create(user=self.user, name=f"Chat {i}")
            
        data = {'name': 'Chat 4'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ChatDetailAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            name='Test User'
        )
        self.client.force_authenticate(user=self.user)
        self.chat = Chat.objects.create(user=self.user, name="Test Chat")
        self.url = reverse('chat-detail', args=[self.chat.chat_id])

    def test_get_chat_detail(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chat']['name'], "Test Chat")

    def test_update_chat_name(self):
        data = {'name': 'Updated Chat'}
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.chat.refresh_from_db()
        self.assertEqual(self.chat.name, 'Updated Chat')

    @patch('chat_app.views.rag_service')
    def test_delete_chat(self, mock_rag_service):
        # Mock RAG service
        mock_rag_instance = MagicMock()
        mock_rag_service.return_value = mock_rag_instance
        
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Chat.objects.count(), 0)
        
        # Verify RAG cleanup was called
        mock_rag_instance.destroy_chat.assert_called_once()

class MessageQueryAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123',
            name='Test User'
        )
        self.client.force_authenticate(user=self.user)
        self.chat = Chat.objects.create(user=self.user, name="Test Chat")
        self.url = reverse('message-query', args=[self.chat.chat_id])

    @patch('chat_app.views.rag_service')
    def test_first_query(self, mock_rag_service):
        # Mock RAG service
        mock_rag_instance = MagicMock()
        mock_rag_instance.first_query.return_value = "AI Response"
        mock_rag_service.return_value = mock_rag_instance
        
        data = {'query': 'Hello'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message']['response'], "AI Response")
        
        # Verify message saved
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        content = message.get_content()
        self.assertEqual(content['prompt'], 'Hello')
        self.assertEqual(content['response'], 'AI Response')

    @patch('chat_app.views.rag_service')
    def test_followup_query(self, mock_rag_service):
        # Create existing message
        msg = Message.objects.create(chat=self.chat)
        msg.set_content("Prev Query", "Prev Response")
        msg.save()
        
        # Mock RAG service
        mock_rag_instance = MagicMock()
        mock_rag_instance.followup_query.return_value = "AI Followup Response"
        mock_rag_service.return_value = mock_rag_instance
        
        data = {'query': 'Followup'}
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify RAG followup called
        mock_rag_instance.followup_query.assert_called_once()
