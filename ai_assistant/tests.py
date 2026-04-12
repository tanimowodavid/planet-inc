from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import AIConversation, AIMessage
from unittest.mock import patch

User = get_user_model()


class AIConversationModelTests(TestCase):
    """Test AIConversation model core functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_multiple_conversations_per_user(self):
        """Test that users can have multiple conversations"""
        conv1 = AIConversation.objects.create(user=self.user)
        conv2 = AIConversation.objects.create(user=self.user)
        
        user_conversations = AIConversation.objects.filter(user=self.user)
        self.assertEqual(user_conversations.count(), 2)
        self.assertIn(conv1, user_conversations)
        self.assertIn(conv2, user_conversations)


class AIMessageModelTests(TestCase):
    """Test AIMessage model core functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.conversation = AIConversation.objects.create(user=self.user)

    def test_message_ordering(self):
        """Test that messages are ordered by creation time"""
        msg1 = AIMessage.objects.create(
            conversation=self.conversation,
            role='user',
            content='First message'
        )
        msg2 = AIMessage.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='Second message'
        )
        msg3 = AIMessage.objects.create(
            conversation=self.conversation,
            role='user',
            content='Third message'
        )
        
        messages = self.conversation.messages.all()
        self.assertEqual(list(messages), [msg1, msg2, msg3])

    def test_message_deletion_with_conversation(self):
        """Test that messages are deleted when conversation is deleted"""
        message = AIMessage.objects.create(
            conversation=self.conversation,
            role='user',
            content='Test message'
        )
        message_id = message.id
        
        self.conversation.delete()
        
        self.assertFalse(AIMessage.objects.filter(id=message_id).exists())


class AIConversationAPITests(APITestCase):
    """Test AI Conversation API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_chat_without_conversation_id(self):
        """Test creating a new conversation via chat"""
        with patch('ai_assistant.utils.find_relevant_products') as mock_products:
            with patch('ai_assistant.views.openai.OpenAI') as mock_openai:
                mock_products.return_value = "Product 1: Test Product"
                
                mock_client = mock_openai.return_value
                mock_response = mock_client.chat.completions.create.return_value
                mock_response.choices = [type('Choice', (), {'message': type('Message', (), {'content': 'Hello! How can I help?'})()})]
                
                data = {'message': 'Hello'}
                response = self.client.post('/api/ai/chat/', data)
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn('conversation_id', response.data)
                self.assertIn('new_message', response.data)

    def test_chat_with_existing_conversation(self):
        """Test sending message to existing conversation"""
        conversation = AIConversation.objects.create(user=self.user)
        AIMessage.objects.create(
            conversation=conversation,
            role='user',
            content='Previous message'
        )
        
        with patch('ai_assistant.utils.find_relevant_products') as mock_products:
            with patch('ai_assistant.views.openai.OpenAI') as mock_openai:
                mock_products.return_value = "Product 1: Test Product"
                
                mock_client = mock_openai.return_value
                mock_response = mock_client.chat.completions.create.return_value
                mock_response.choices = [type('Choice', (), {'message': type('Message', (), {'content': 'Continuing conversation'})()})]
                
                data = {
                    'message': 'Tell me more',
                    'conversation_id': conversation.id
                }
                response = self.client.post('/api/ai/chat/', data)
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['conversation_id'], conversation.id)

    def test_chat_saves_user_message(self):
        """Test that user message is saved"""
        with patch('ai_assistant.utils.find_relevant_products') as mock_products:
            with patch('ai_assistant.views.openai.OpenAI') as mock_openai:
                mock_products.return_value = "Products"
                
                mock_client = mock_openai.return_value
                mock_response = mock_client.chat.completions.create.return_value
                mock_response.choices = [type('Choice', (), {'message': type('Message', (), {'content': 'Response'})()})]
                
                data = {'message': 'Test message'}
                response = self.client.post('/api/ai/chat/', data)
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                conversation_id = response.data['conversation_id']
                conversation = AIConversation.objects.get(id=conversation_id)
                
                # Check that messages were saved
                self.assertGreaterEqual(conversation.messages.count(), 2)

    def test_chat_saves_assistant_response(self):
        """Test that assistant response is saved"""
        with patch('ai_assistant.utils.find_relevant_products') as mock_products:
            with patch('ai_assistant.views.openai.OpenAI') as mock_openai:
                mock_products.return_value = "Products"
                expected_response = 'A response from Claude'
                
                mock_client = mock_openai.return_value
                mock_response = mock_client.chat.completions.create.return_value
                mock_response.choices = [type('Choice', (), {'message': type('Message', (), {'content': expected_response})()})]
                
                data = {'message': 'Hello'}
                response = self.client.post('/api/ai/chat/', data)
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['new_message']['content'], expected_response)

    def test_chat_unauthenticated(self):
        """Test chat without authentication"""
        self.client.force_authenticate(user=None)
        data = {'message': 'Hello'}
        response = self.client.post('/api/ai/chat/', data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_chat_rate_limit_error(self):
        """Test handling of rate limit errors"""
        with patch('ai_assistant.utils.find_relevant_products') as mock_products:
            with patch('ai_assistant.views.openai.OpenAI') as mock_openai:
                mock_products.return_value = "Products"
                
                mock_client = mock_openai.return_value
                mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
                
                data = {'message': 'Hello'}
                response = self.client.post('/api/ai/chat/', data)
                
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                # Should return error message instead of crashing
                self.assertIn('new_message', response.data)
                self.assertIn('conversation_id', response.data)
                self.assertIn("I'm having trouble reaching the Galactic Database", 
                            response.data['new_message']['content'])

    def test_chat_conversation_isolation(self):
        """Test that conversations are isolated per user"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='User'
        )
        
        self_conversation = AIConversation.objects.create(user=self.user)
        other_conversation = AIConversation.objects.create(user=other_user)
        
        user_conversations = AIConversation.objects.filter(user=self.user)
        
        self.assertIn(self_conversation, user_conversations)
        self.assertNotIn(other_conversation, user_conversations)
