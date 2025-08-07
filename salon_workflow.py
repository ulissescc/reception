"""
Level 5 Agentic Workflow for Salon Receptionist
Autonomous multi-message booking system with background task processing
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

# from agno import Workflow  # May not be available in current Agno version
# Using simple class instead
from receptionist import SalonReceptionist
from message_queue import message_queue, MessageQueue
from database import Service

class WorkflowState(Enum):
    IDLE = "idle"
    CHECKING_AVAILABILITY = "checking_availability"
    WAITING_SERVICE_CHOICE = "waiting_service_choice" 
    WAITING_TIME_CHOICE = "waiting_time_choice"
    WAITING_NAME = "waiting_name"
    CREATING_APPOINTMENT = "creating_appointment"
    COMPLETED = "completed"

@dataclass
class BookingContext:
    phone: str
    client_name: Optional[str] = None
    service_name: Optional[str] = None
    service_id: Optional[int] = None
    date_requested: Optional[str] = None
    time_requested: Optional[str] = None
    available_slots: List[str] = field(default_factory=list)
    state: WorkflowState = WorkflowState.IDLE
    last_message: str = ""
    created_at: datetime = field(default_factory=datetime.now)

class SalonWorkflow:
    """Level 5 Agentic Workflow for autonomous salon booking"""
    
    def __init__(self):
        self.name = "SalonWorkflow"
        self.receptionist = SalonReceptionist()
        self.message_queue = message_queue
        self.active_bookings: Dict[str, BookingContext] = {}
        
    async def process_message(self, phone: str, message: str, user_name: Optional[str] = None) -> str:
        """Main entry point - processes incoming messages and manages workflow"""
        
        # Get or create booking context
        if phone not in self.active_bookings:
            self.active_bookings[phone] = BookingContext(phone=phone, client_name=user_name)
        
        context = self.active_bookings[phone]
        context.last_message = message
        
        # Update client name if provided
        if user_name and not context.client_name:
            context.client_name = user_name
        
        # Analyze message intent
        intent = await self._analyze_message_intent(message, context)
        
        # Route to appropriate handler
        if intent["type"] == "booking_request":
            return await self._handle_booking_request(context, intent)
        elif intent["type"] == "service_choice":
            return await self._handle_service_choice(context, intent)
        elif intent["type"] == "time_choice":
            return await self._handle_time_choice(context, intent)
        elif intent["type"] == "name_provided":
            return await self._handle_name_provided(context, intent)
        elif intent["type"] == "general_inquiry":
            return await self._handle_general_inquiry(context, message)
        else:
            # Default to receptionist for other cases
            return self.receptionist.process_message(phone, message, user_name)
    
    async def _analyze_message_intent(self, message: str, context: BookingContext) -> Dict[str, Any]:
        """Analyze message to determine intent and extract parameters"""
        message_lower = message.lower()
        
        # Booking request patterns
        booking_keywords = ["marcar", "agendar", "quero", "consulta", "appointment", "book"]
        service_keywords = {
            "manicure básica": "básica",
            "manicure gel": "gel", 
            "gel": "gel",
            "básica": "básica",
            "pedicure": "pedicure",
            "acrylic": "acrylic"
        }
        
        # Check for booking request
        if any(keyword in message_lower for keyword in booking_keywords):
            intent = {"type": "booking_request"}
            
            # Extract service if mentioned
            for service, key in service_keywords.items():
                if key in message_lower:
                    intent["service"] = service
                    break
            
            # Extract date/time if mentioned
            if "amanhã" in message_lower or "tomorrow" in message_lower:
                intent["date"] = "tomorrow"
            if "hoje" in message_lower or "today" in message_lower:
                intent["date"] = "today"
                
            # Extract time patterns (14h, 14:00, 2pm, etc.)
            import re
            time_patterns = [
                r"(\d{1,2})[h:](\d{2})?",  # 14h or 14:00
                r"(\d{1,2})\s*pm",         # 2pm
                r"(\d{1,2})\s*am",         # 10am
            ]
            for pattern in time_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    intent["time"] = match.group(0)
                    break
                    
            return intent
        
        # Service choice during booking flow
        if context.state == WorkflowState.WAITING_SERVICE_CHOICE:
            for service, key in service_keywords.items():
                if key in message_lower:
                    return {"type": "service_choice", "service": service}
        
        # Time choice during booking flow  
        if context.state == WorkflowState.WAITING_TIME_CHOICE:
            import re
            time_match = re.search(r"(\d{1,2})[h:]?(\d{2})?", message)
            if time_match:
                return {"type": "time_choice", "time": time_match.group(0)}
        
        # Name provided during flow
        if context.state == WorkflowState.WAITING_NAME:
            # Simple name detection - not just single words, could be "meu nome é Ana"
            if len(message.split()) <= 4:  # Reasonable name length
                return {"type": "name_provided", "name": message}
        
        # General inquiry
        return {"type": "general_inquiry"}
    
    async def _handle_booking_request(self, context: BookingContext, intent: Dict) -> str:
        """Handle initial booking request with autonomous workflow"""
        
        # Send immediate acknowledgment
        await self.message_queue.send_immediate(
            context.phone,
            "Perfeito! Vou ajudar com o seu agendamento. ✨"
        )
        
        # Check if we have service info
        if "service" not in intent:
            # Need to ask for service
            context.state = WorkflowState.WAITING_SERVICE_CHOICE
            await self.message_queue.send_message(
                context.phone,
                "Que serviço te interessa? Temos:\n\n💅 Manicure Básica (€23, 45min)\n💅 Manicure em Gel (€32, 60min)\n💅 Pedicure Básica (€25, 45min)",
                delay_seconds=1.5
            )
            return ""  # Don't return anything - messages sent via queue
        
        # We have service, proceed to availability check
        context.service_name = intent["service"]
        context.state = WorkflowState.CHECKING_AVAILABILITY
        
        # Start availability check in background
        asyncio.create_task(self._check_availability_and_respond(context, intent))
        
        return ""  # Messages sent via background task
    
    async def _check_availability_and_respond(self, context: BookingContext, intent: Dict):
        """Background task to check availability and send results"""
        
        # Send "checking" message
        await self.message_queue.send_message(
            context.phone,
            "Deixa-me verificar os horários disponíveis... ⏳",
            delay_seconds=0.5
        )
        
        # Simulate availability check (in real implementation, call actual method)
        await asyncio.sleep(2)  # Simulate API call delay
        
        # Get tomorrow's date
        tomorrow = datetime.now() + timedelta(days=1)
        date_str = tomorrow.strftime("%d/%m/%Y")
        
        # Mock available slots (in real implementation, call receptionist.check_availability)
        available_times = ["09:00", "10:30", "14:00", "14:15", "15:30", "16:00"]
        context.available_slots = available_times
        context.state = WorkflowState.WAITING_TIME_CHOICE
        
        # Send available times
        slots_text = f"Ótimo! Para {context.service_name} amanhã ({date_str}), tenho estes horários:\n\n"
        slots_text += "\\n".join([f"• {time}" for time in available_times[:4]])  # Show first 4
        slots_text += "\\n\\nQual prefere?"
        
        await self.message_queue.send_message(
            context.phone,
            slots_text,
            delay_seconds=1.0
        )
    
    async def _handle_service_choice(self, context: BookingContext, intent: Dict) -> str:
        """Handle service selection"""
        context.service_name = intent["service"] 
        context.state = WorkflowState.CHECKING_AVAILABILITY
        
        # Start background availability check
        asyncio.create_task(self._check_availability_and_respond(context, {}))
        
        return ""
    
    async def _handle_time_choice(self, context: BookingContext, intent: Dict) -> str:
        """Handle time selection and create appointment"""
        context.time_requested = intent["time"]
        context.state = WorkflowState.CREATING_APPOINTMENT
        
        # Check if we need name
        if not context.client_name:
            context.state = WorkflowState.WAITING_NAME
            await self.message_queue.send_immediate(
                context.phone,
                f"Perfeito! {context.time_requested} está ótimo. Posso saber o seu nome para confirmar o agendamento?"
            )
            return ""
        
        # We have all info - create appointment
        asyncio.create_task(self._create_appointment_and_confirm(context))
        return ""
    
    async def _handle_name_provided(self, context: BookingContext, intent: Dict) -> str:
        """Handle name provision and complete booking"""
        context.client_name = intent["name"]
        context.state = WorkflowState.CREATING_APPOINTMENT
        
        # Create appointment
        asyncio.create_task(self._create_appointment_and_confirm(context))
        return ""
    
    async def _create_appointment_and_confirm(self, context: BookingContext):
        """Background task to create appointment and send confirmation"""
        
        # Send creating message
        await self.message_queue.send_message(
            context.phone,
            "A confirmar o seu agendamento... ⏳",
            delay_seconds=0.5
        )
        
        # Simulate appointment creation
        await asyncio.sleep(2)
        
        # Get tomorrow's date
        tomorrow = datetime.now() + timedelta(days=1)
        formatted_date = tomorrow.strftime("%d/%m/%Y")
        
        # In real implementation, call actual booking method:
        # result = self.receptionist.create_appointment_tool(
        #     client_phone=context.phone,
        #     client_name=context.client_name,
        #     service_name=context.service_name,
        #     date_str=formatted_date,
        #     time_str=context.time_requested
        # )
        
        # Mock successful booking for demo
        success = True
        
        if success:
            # Send confirmation
            confirmation = f"✅ **Agendamento Confirmado!**\\n\\n"
            confirmation += f"👤 Cliente: {context.client_name}\\n"
            confirmation += f"💅 Serviço: {context.service_name}\\n" 
            confirmation += f"📅 Data: {formatted_date} às {context.time_requested}\\n\\n"
            confirmation += f"Márcia foi notificada automaticamente. Até breve! 😊"
            
            await self.message_queue.send_message(
                context.phone,
                confirmation,
                delay_seconds=1.0
            )
            
            context.state = WorkflowState.COMPLETED
        else:
            # Send error message
            await self.message_queue.send_message(
                context.phone,
                "❌ Houve um problema ao confirmar o agendamento. Pode tentar novamente?",
                delay_seconds=1.0
            )
            context.state = WorkflowState.IDLE
    
    async def _handle_general_inquiry(self, context: BookingContext, message: str) -> str:
        """Handle general questions using standard receptionist"""
        response = self.receptionist.process_message(context.phone, message, context.client_name)
        
        # Send via message queue for consistency
        await self.message_queue.send_immediate(context.phone, response)
        return ""
    
    def get_booking_status(self, phone: str) -> Optional[Dict]:
        """Get current booking status for a phone number"""
        if phone not in self.active_bookings:
            return None
            
        context = self.active_bookings[phone]
        return {
            "phone": context.phone,
            "client_name": context.client_name,
            "service_name": context.service_name,
            "state": context.state.value,
            "created_at": context.created_at.isoformat()
        }

# Global workflow instance
salon_workflow = SalonWorkflow()