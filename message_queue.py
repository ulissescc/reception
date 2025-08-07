"""
Message Queue System for Autonomous WhatsApp Communication
Handles sequential message delivery with proper timing and delivery confirmation
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

class MessageStatus(Enum):
    PENDING = "pending"
    SENT = "sent" 
    FAILED = "failed"
    CONFIRMED = "confirmed"

@dataclass
class QueuedMessage:
    phone: str
    message: str
    delay_seconds: float = 1.0
    status: MessageStatus = field(default=MessageStatus.PENDING)
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

class MessageQueue:
    """Autonomous message queue for sending sequential WhatsApp messages"""
    
    def __init__(self):
        self.instance_id = "3E3D83F891B75008327D764AFE850DAC"
        self.client_token = "Fbb71b79c5fbe4568ad040a6d609bd5f2S"
        self.base_url = f"https://api.z-api.io/instances/{self.instance_id}/token/14BDD904C38209CB129D97A7"
        self.active_queues: Dict[str, List[QueuedMessage]] = {}
        self.processing_locks: Dict[str, asyncio.Lock] = {}
    
    async def send_message(self, phone: str, message: str, delay_seconds: float = 1.0) -> bool:
        """Add message to queue and process immediately"""
        queued_msg = QueuedMessage(
            phone=phone,
            message=message, 
            delay_seconds=delay_seconds
        )
        
        # Initialize queue for this phone if needed
        if phone not in self.active_queues:
            self.active_queues[phone] = []
            self.processing_locks[phone] = asyncio.Lock()
        
        # Add to queue
        self.active_queues[phone].append(queued_msg)
        
        # Process queue asynchronously (don't await - let it run in background)
        asyncio.create_task(self._process_phone_queue(phone))
        
        return True
    
    async def send_immediate(self, phone: str, message: str) -> bool:
        """Send message immediately without queueing"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/send-text",
                    json={"phone": phone, "message": message},
                    headers={
                        "Content-Type": "application/json",
                        "Client-Token": self.client_token
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    print(f"✅ Immediate message sent to {phone}: {message[:50]}...")
                    return True
                else:
                    print(f"❌ Failed to send immediate message: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending immediate message: {str(e)}")
            return False
    
    async def _process_phone_queue(self, phone: str):
        """Process all queued messages for a specific phone number"""
        async with self.processing_locks[phone]:
            while self.active_queues[phone]:
                message = self.active_queues[phone][0]  # Get first message
                
                # Wait for delay
                await asyncio.sleep(message.delay_seconds)
                
                # Send message
                success = await self._send_queued_message(message)
                
                if success:
                    # Remove from queue
                    self.active_queues[phone].pop(0)
                    print(f"✅ Queued message sent to {phone}: {message.message[:50]}...")
                else:
                    # Handle retry logic
                    message.retry_count += 1
                    if message.retry_count >= message.max_retries:
                        print(f"❌ Message failed after {message.max_retries} retries, removing from queue")
                        self.active_queues[phone].pop(0)
                    else:
                        print(f"⚠️ Message failed, retrying ({message.retry_count}/{message.max_retries})")
                        await asyncio.sleep(2.0)  # Wait before retry
    
    async def _send_queued_message(self, message: QueuedMessage) -> bool:
        """Send a single queued message via Z-API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/send-text",
                    json={"phone": message.phone, "message": message.message},
                    headers={
                        "Content-Type": "application/json",
                        "Client-Token": self.client_token
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    message.status = MessageStatus.SENT
                    message.sent_at = datetime.now()
                    return True
                else:
                    message.status = MessageStatus.FAILED
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending queued message: {str(e)}")
            message.status = MessageStatus.FAILED
            return False
    
    async def clear_queue(self, phone: str):
        """Clear all pending messages for a phone number"""
        if phone in self.active_queues:
            self.active_queues[phone].clear()
    
    def get_queue_status(self, phone: str) -> Dict:
        """Get queue status for a phone number"""
        if phone not in self.active_queues:
            return {"queue_length": 0, "messages": []}
        
        messages = []
        for msg in self.active_queues[phone]:
            messages.append({
                "message": msg.message[:50] + "..." if len(msg.message) > 50 else msg.message,
                "status": msg.status.value,
                "delay": msg.delay_seconds,
                "retries": msg.retry_count
            })
        
        return {
            "queue_length": len(self.active_queues[phone]),
            "messages": messages
        }

# Global message queue instance
message_queue = MessageQueue()