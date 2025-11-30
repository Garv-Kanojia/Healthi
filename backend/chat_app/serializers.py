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
    files = serializers.SerializerMethodField()
    prompt = serializers.SerializerMethodField()
    response = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = ['id', 'prompt', 'response', 'files', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def get_prompt(self, obj):
        """Extract and decrypt prompt from content."""
        content = obj.get_content()
        return content.get('prompt', '')
    
    def get_response(self, obj):
        """Extract and decrypt response from content."""
        content = obj.get_content()
        return content.get('response', '')

    def get_files(self, obj):
        """Return list of file names."""
        return [file.file_name for file in obj.files.all()]


class ChatSerializer(serializers.ModelSerializer):
    """
    Serializer for Chat model.
    """
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Chat
        fields = ['id', 'chat_id', 'name', 'patient_info', 'created_at', 'message_count']
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
        fields = ['id', 'chat_id', 'name', 'patient_info', 'created_at', 'message_count', 'messages']
        read_only_fields = ['id', 'chat_id', 'created_at']
    
    def get_message_count(self, obj):
        """Get total number of messages in the chat."""
        return obj.messages.count()


class ChatCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new chat.
    """
    # Patient info options
    use_profile_data = serializers.BooleanField(required=False, write_only=True)
    age = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    gender = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    clinical_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    
    class Meta:
        model = Chat
        fields = ['name', 'use_profile_data', 'age', 'gender', 'clinical_notes']
    
    def validate(self, attrs):
        """
        Validate that either use_profile_data is True OR manual data is provided OR all are skipped.
        """
        use_profile_data = attrs.get('use_profile_data', False)
        age = attrs.get('age')
        gender = attrs.get('gender')
        clinical_notes = attrs.get('clinical_notes')
        
        # If use_profile_data is True, manual fields should not be provided
        if use_profile_data and (age is not None or gender or clinical_notes):
            raise serializers.ValidationError(
                "Cannot provide manual patient data when use_profile_data is True"
            )
        
        return attrs
    
    def create(self, validated_data):
        """
        Create chat with patient info from profile or manual input.
        """
        use_profile_data = validated_data.pop('use_profile_data', False)
        age = validated_data.pop('age', None)
        gender = validated_data.pop('gender', None)
        clinical_notes = validated_data.pop('clinical_notes', None)
        
        user = self.context['request'].user
        patient_info_parts = []
        
        if use_profile_data:
            # Use data from user profile
            if user.age:
                patient_info_parts.append(f"Age: {user.age}")
            if user.gender:
                patient_info_parts.append(f"Gender: {user.gender}")
            
            # Get medical history if exists
            try:
                medical_history = user.medical_history
                if medical_history.medical_notes:
                    patient_info_parts.append(f"Clinical Notes: {medical_history.medical_notes}")
            except:
                pass  # No medical history
        else:
            # Use manual input
            if age is not None:
                patient_info_parts.append(f"Age: {age}")
            if gender:
                patient_info_parts.append(f"Gender: {gender}")
            if clinical_notes:
                patient_info_parts.append(f"Clinical Notes: {clinical_notes}")
        
        # Combine patient info
        patient_info = " | ".join(patient_info_parts) if patient_info_parts else None
        
        # Create chat
        chat = Chat.objects.create(
            user=user,
            name=validated_data.get('name', 'Chat'),
            patient_info=patient_info
        )
        
        return chat


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
    prompt = serializers.CharField()
    response = serializers.CharField()
    created_at = serializers.DateTimeField()