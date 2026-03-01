"""
Notification Services Package
"""

from app.services.notifications.email_service import EmailService, get_email_service

__all__ = ['EmailService', 'get_email_service']
