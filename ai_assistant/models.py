from django.db import models
from django.conf import settings


class AIConversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat with {self.user.username} on {self.created_at.strftime('%Y-%m-%d')}"

class AIMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'AI'),
    )
    conversation = models.ForeignKey(AIConversation, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
