"""
Email Notification Service using Resend API
"""

import logging
from typing import Optional, Dict
import httpx
from datetime import datetime, UTC

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email notification service using Resend API.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'RESEND_CS_SUPPORT_API_KEY', None)
        self.from_email = getattr(settings, 'RESEND_FROM_EMAIL', 'support@intakely.xyz')
        self.from_name = getattr(settings, 'RESEND_FROM_NAME', 'TrueVow SETTLE')
        self.api_url = "https://api.resend.com/emails"
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email via Resend API.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Plain text fallback (optional)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        
        if not self.api_key:
            logger.warning("Resend API key not configured, skipping email send")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": f"{self.from_name} <{self.from_email}>",
                        "to": [to_email],
                        "subject": subject,
                        "html": html_content,
                        "text": text_content or self._strip_html(html_content)
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Email sent successfully to {to_email}: {subject}")
                    return True
                else:
                    logger.error(
                        f"Failed to send email to {to_email}: "
                        f"Status {response.status_code}, Response: {response.text}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}", exc_info=True)
            return False
    
    async def send_founding_member_welcome(
        self,
        to_email: str,
        law_firm_name: str,
        api_key: str
    ) -> bool:
        """
        Send welcome email to approved Founding Member with API key.
        
        Args:
            to_email: Attorney email
            law_firm_name: Law firm name
            api_key: Generated API key
            
        Returns:
            True if email sent successfully
        """
        
        subject = "Welcome to SETTLE™ Founding Member Program"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">Welcome to SETTLE™</h1>
                
                <p>Dear {law_firm_name},</p>
                
                <p>Congratulations! You've been approved as a <strong>Founding Member</strong> of the SETTLE™ settlement database.</p>
                
                <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h2 style="margin-top: 0; color: #1f2937;">Your API Key</h2>
                    <p style="font-family: monospace; background-color: #fff; padding: 10px; border: 1px solid #d1d5db; border-radius: 4px; word-break: break-all;">
                        {api_key}
                    </p>
                    <p style="color: #dc2626; font-weight: bold;">⚠️ Store this securely - it won't be shown again!</p>
                </div>
                
                <h3 style="color: #1f2937;">Your Founding Member Benefits:</h3>
                <ul>
                    <li>✅ Unlimited settlement range queries</li>
                    <li>✅ Unlimited report generation</li>
                    <li>✅ Free forever (no subscription fees)</li>
                    <li>✅ Priority support</li>
                    <li>✅ Early access to new features</li>
                    <li>✅ Voting rights on database policies</li>
                </ul>
                
                <h3 style="color: #1f2937;">Getting Started:</h3>
                <ol>
                    <li>Add this API key to your application's environment variables</li>
                    <li>Include it in the <code>Authorization: Bearer [api_key]</code> header</li>
                    <li>Start making queries to: <code>https://settle.truevow.law/api/v1/query/estimate</code></li>
                </ol>
                
                <p>Read the full API documentation at: <a href="https://settle.truevow.law/docs">https://settle.truevow.law/docs</a></p>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #6b7280;">
                    Questions? Contact us at support@truevow.law<br>
                    TrueVow SETTLE™ - Ethical settlement intelligence for attorneys
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)
    
    async def send_waitlist_rejection(
        self,
        to_email: str,
        law_firm_name: str,
        reason: str
    ) -> bool:
        """
        Send rejection email to waitlist applicant.
        
        Args:
            to_email: Attorney email
            law_firm_name: Law firm name
            reason: Rejection reason
            
        Returns:
            True if email sent successfully
        """
        
        subject = "SETTLE™ Waitlist Application Update"
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2563eb;">SETTLE™ Waitlist Update</h1>
                
                <p>Dear {law_firm_name},</p>
                
                <p>Thank you for your interest in the SETTLE™ Founding Member program.</p>
                
                <p>After reviewing your application, we're unable to approve it at this time for the following reason:</p>
                
                <div style="background-color: #fef2f2; padding: 15px; border-left: 4px solid #dc2626; margin: 20px 0;">
                    <p style="margin: 0; color: #991b1b;">{reason}</p>
                </div>
                
                <p>If you believe this was an error or would like to discuss your application, please contact us at support@truevow.law.</p>
                
                <p>You can also stay updated on SETTLE™ by visiting our website: <a href="https://settle.truevow.law">https://settle.truevow.law</a></p>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #6b7280;">
                    TrueVow SETTLE™ - Ethical settlement intelligence for attorneys
                </p>
            </div>
        </body>
        </html>
        """
        
        return await self.send_email(to_email, subject, html_content)
    
    def _strip_html(self, html: str) -> str:
        """
        Simple HTML tag stripper for plain text fallback.
        """
        import re
        return re.sub(r'<[^>]+>', '', html).strip()


# Singleton instance
_email_service = None

def get_email_service() -> EmailService:
    """Get email service singleton instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
