"""
Internal Ops Service Client

Client for communicating with the Internal Ops Service for:
- Logging activity (for time tracking)
- Creating tasks
- Sending notifications
"""

import logging
from typing import Dict, Optional
from datetime import datetime

from app.core.service_auth import get_internal_ops_service_client

logger = logging.getLogger(__name__)


class InternalOpsServiceClient:
    """
    Client for Internal Ops Service integration.
    
    The Internal Ops Service handles:
    - Task management
    - Time tracking
    - Team chat & notifications
    - Internal shared inbox
    """
    
    def __init__(self):
        """Initialize Internal Ops Service client"""
        self.client = get_internal_ops_service_client()
    
    async def log_activity(
        self,
        user_id: str,
        activity_type: str,
        duration_seconds: int,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Log activity for time tracking.
        
        Args:
            user_id: User ID
            activity_type: Type of activity (e.g., "settle_query", "settle_contribution_review")
            duration_seconds: Duration in seconds
            metadata: Additional metadata
            
        Returns:
            Response from Internal Ops Service
            
        Example:
            await internal_ops_client.log_activity(
                user_id="user_123",
                activity_type="settle_query",
                duration_seconds=2,
                metadata={"query_id": "query_456", "confidence": "high"}
            )
        """
        try:
            response = await self.client.post(
                "/api/v1/time/activity",
                json={
                    "user_id": user_id,
                    "activity_type": activity_type,
                    "duration_seconds": duration_seconds,
                    "service": "settle",
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
            
            logger.info(
                f"Activity logged to Internal Ops: user={user_id}, "
                f"type={activity_type}, duration={duration_seconds}s"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to log activity to Internal Ops: {str(e)}")
            # Don't raise - activity logging is non-critical
            return {"success": False, "error": str(e)}
    
    async def create_task(
        self,
        task_title: str,
        assigned_to: str,
        task_type: str,
        description: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a task in Internal Ops.
        
        Args:
            task_title: Task title
            assigned_to: User ID to assign task to
            task_type: Type of task (e.g., "contribution_review", "support_inquiry")
            description: Task description
            priority: Priority level (low, medium, high, urgent)
            due_date: Due date
            metadata: Additional metadata
            
        Returns:
            Response from Internal Ops Service
            
        Example:
            await internal_ops_client.create_task(
                task_title="Review SETTLE contribution",
                assigned_to="admin_user_123",
                task_type="contribution_review",
                description="Review contribution ID: contrib_456 for PHI/PII",
                priority="high",
                metadata={"contribution_id": "contrib_456"}
            )
        """
        try:
            response = await self.client.post(
                "/api/v1/tasks",
                json={
                    "task_title": task_title,
                    "assigned_to": assigned_to,
                    "task_type": task_type,
                    "description": description,
                    "priority": priority,
                    "due_date": due_date.isoformat() + "Z" if due_date else None,
                    "service": "settle",
                    "metadata": metadata or {}
                }
            )
            
            logger.info(f"Task created in Internal Ops: {task_title} -> {assigned_to}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to create task in Internal Ops: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        priority: str = "normal",
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Send notification to user.
        
        Args:
            user_id: User ID
            notification_type: Type of notification (e.g., "task_alert", "system_alert")
            title: Notification title
            message: Notification message
            priority: Priority level (low, normal, high, urgent)
            metadata: Additional metadata
            
        Returns:
            Response from Internal Ops Service
            
        Example:
            await internal_ops_client.send_notification(
                user_id="user_123",
                notification_type="task_alert",
                title="New SETTLE contribution to review",
                message="A new contribution has been submitted and requires review",
                priority="high",
                metadata={"contribution_id": "contrib_456"}
            )
        """
        try:
            response = await self.client.post(
                "/api/v1/notifications",
                json={
                    "user_id": user_id,
                    "notification_type": notification_type,
                    "title": title,
                    "message": message,
                    "priority": priority,
                    "service": "settle",
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
            
            logger.info(f"Notification sent to user {user_id}: {title}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def log_error(
        self,
        user_id: str,
        error_type: str,
        error_message: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Log error for tracking and alerting.
        
        Args:
            user_id: User ID
            error_type: Type of error
            error_message: Error message
            metadata: Additional metadata
            
        Returns:
            Response from Internal Ops Service
        """
        try:
            response = await self.client.post(
                "/api/v1/errors/log",
                json={
                    "user_id": user_id,
                    "error_type": error_type,
                    "error_message": error_message,
                    "service": "settle",
                    "metadata": metadata or {},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )
            
            logger.info(f"Error logged: {error_type} for user {user_id}")
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to log error to Internal Ops: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close the client connection"""
        await self.client.close()

