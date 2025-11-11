from rest_framework import serializers
from .models import Chat, Message, MessageFile


class MessageFileSerializer(serializers.ModelSerializer):
    """
    Serializer for MessageFile model.
    """
    class Meta:
        model = MessageFile
        fields = ['id', 'file_type', 'file_name', 'file_size']
        read_only_fields = ['id']


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model with decrypted content.
    """
    files = MessageFileSerializer(many=True, read_only=True)
    prompt = serializers.SerializerMethodField()
    response = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'count', 'prompt', 'response', 'files', 'created_at']
        read_only_fields = ['id', 'count', 'created_at']
    
    def get_prompt(self, obj):
        """Extract and decrypt prompt from content."""
        content = obj.get_content()
        return content.get('prompt', '')
    
    def get_response(self, obj):
        """Extract and decrypt response from content."""
        content = obj.get_content()
        return content.get('response', '')


class ChatSerializer(serializers.ModelSerializer):
    """
    Serializer for Chat model.
    """
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = ['id', 'chat_id', 'name', 'created_at', 'message_count']
        read_only_fields = ['id', 'chat_id', 'created_at']
    
    def get_message_count(self, obj):
        """Get total number of messages in the chat."""
        return obj.messages.count()


class ChatDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Chat with messages.
    """
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = ['id', 'chat_id', 'name', 'created_at', 'message_count', 'messages']
        read_only_fields = ['id', 'chat_id', 'created_at']
    
    def get_message_count(self, obj):
        """Get total number of messages in the chat."""
        return obj.messages.count()


class ChatCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new chat.
    """
    class Meta:
        model = Chat
        fields = ['name']


class MessageQuerySerializer(serializers.Serializer):
    """
    Serializer for validating incoming query requests.
    """
    query = serializers.CharField(required=True, max_length=5000)
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        max_length=7  # Max 5 images + 2 PDFs
    )


class MessageResponseSerializer(serializers.Serializer):
    """
    Serializer for message response.
    """
    count = serializers.IntegerField()
    prompt = serializers.CharField()
    response = serializers.CharField()
    created_at = serializers.DateTimeField()