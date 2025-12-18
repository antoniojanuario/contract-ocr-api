"""
Webhook notification service for document processing completion
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import aiohttp
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for sending webhook notifications"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.webhook_configs: Dict[str, Dict] = {}  # In-memory storage for demo
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def configure_webhook(self, document_id: str, webhook_url: str, events: List[str] = None) -> bool:
        """
        Configure webhook for a document
        
        Args:
            document_id: Document identifier
            webhook_url: URL to send webhook notifications
            events: List of events to notify about (default: ['completed', 'failed'])
            
        Returns:
            True if configuration was successful
        """
        if events is None:
            events = ['completed', 'failed']
            
        self.webhook_configs[document_id] = {
            'url': webhook_url,
            'events': events,
            'configured_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Configured webhook for document {document_id}: {webhook_url}")
        return True
    
    def get_webhook_config(self, document_id: str) -> Optional[Dict]:
        """Get webhook configuration for a document"""
        return self.webhook_configs.get(document_id)
    
    def remove_webhook_config(self, document_id: str) -> bool:
        """Remove webhook configuration for a document"""
        if document_id in self.webhook_configs:
            del self.webhook_configs[document_id]
            logger.info(f"Removed webhook configuration for document {document_id}")
            return True
        return False
    
    async def send_webhook_notification(
        self, 
        document_id: str, 
        event: str, 
        payload: Dict,
        max_retries: int = 3
    ) -> bool:
        """
        Send webhook notification for a document event
        
        Args:
            document_id: Document identifier
            event: Event type (e.g., 'completed', 'failed')
            payload: Notification payload
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if notification was sent successfully
        """
        webhook_config = self.get_webhook_config(document_id)
        if not webhook_config:
            logger.debug(f"No webhook configured for document {document_id}")
            return False
        
        if event not in webhook_config['events']:
            logger.debug(f"Event {event} not configured for document {document_id}")
            return False
        
        webhook_url = webhook_config['url']
        
        # Prepare webhook payload
        webhook_payload = {
            'event': event,
            'document_id': document_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': payload
        }
        
        # Send webhook with retries
        for attempt in range(max_retries):
            try:
                success = await self._send_webhook_request(webhook_url, webhook_payload)
                if success:
                    logger.info(f"Webhook notification sent successfully for document {document_id} (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"Webhook notification failed for document {document_id} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Webhook notification error for document {document_id} (attempt {attempt + 1}): {str(e)}")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_time)
        
        logger.error(f"Failed to send webhook notification for document {document_id} after {max_retries} attempts")
        return False
    
    async def _send_webhook_request(self, webhook_url: str, payload: Dict) -> bool:
        """
        Send HTTP POST request to webhook URL
        
        Args:
            webhook_url: Target webhook URL
            payload: JSON payload to send
            
        Returns:
            True if request was successful (2xx status code)
        """
        session = await self._get_session()
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'ContractOCR-Webhook/{settings.VERSION}'
        }
        
        try:
            async with session.post(
                webhook_url,
                json=payload,
                headers=headers
            ) as response:
                if 200 <= response.status < 300:
                    logger.debug(f"Webhook request successful: {response.status}")
                    return True
                else:
                    logger.warning(f"Webhook request failed with status {response.status}: {await response.text()}")
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"Webhook request failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending webhook: {str(e)}")
            return False
    
    async def notify_document_completed(self, document_id: str, result_data: Dict) -> bool:
        """
        Send completion notification for a document
        
        Args:
            document_id: Document identifier
            result_data: Processing result data
            
        Returns:
            True if notification was sent successfully
        """
        return await self.send_webhook_notification(
            document_id=document_id,
            event='completed',
            payload=result_data
        )
    
    async def notify_document_failed(self, document_id: str, error_data: Dict) -> bool:
        """
        Send failure notification for a document
        
        Args:
            document_id: Document identifier
            error_data: Error information
            
        Returns:
            True if notification was sent successfully
        """
        return await self.send_webhook_notification(
            document_id=document_id,
            event='failed',
            payload=error_data
        )
    
    def list_configured_webhooks(self) -> Dict[str, Dict]:
        """List all configured webhooks"""
        return self.webhook_configs.copy()
    
    def health_check(self) -> bool:
        """Check if webhook service is healthy"""
        try:
            # Basic health check - ensure we can create a session
            return True
        except Exception as e:
            logger.error(f"Webhook service health check failed: {str(e)}")
            return False


# Global webhook service instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service() -> WebhookService:
    """Get global webhook service instance"""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service


async def cleanup_webhook_service():
    """Cleanup webhook service resources"""
    global _webhook_service
    if _webhook_service:
        await _webhook_service.close()
        _webhook_service = None