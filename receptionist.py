"""
Nail Salon AI Receptionist Agent
Built with Agno framework using Level 5 agentic workflows
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from agno.agent import Agent
from agno.storage.sqlite import SqliteStorage
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.models.xai import xAI

from database import init_database, Client, Service, Appointment, AvailabilitySlot
from dotenv import load_dotenv
load_dotenv()

class SalonReceptionist(Agent):
    """
    AI Receptionist agent for nail salon using Agno's built-in features
    """
    
    def __init__(self):
        # Initialize database
        self.engine = init_database()
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Create xAI model instance for memory components
        self.xai_model = xAI(id="grok-3", api_key=os.getenv("XAI_API_KEY"))
        
        # Initialize Agno agent with xAI Grok model, storage and memory
        super().__init__(
            name="SalonReceptionist",
            model=self.xai_model,  # Using shared Grok model instance
            role="Professional nail salon receptionist",
            instructions=[
                "Você é uma recepcionista amigável e profissional do Elegant Nails Spa.",
                "Você ajuda clientes a marcar consultas, responde perguntas sobre serviços e fornece informações do salão.",
                "IMPORTANTE: Sempre responda em PORTUGUÊS. Seja educada, prestativa e eficiente nas suas respostas.",
                "IMPORTANTE: Se um cliente não tem nome no perfil, pergunte o nome dele no início da conversa.",
                "Quando souber o nome do cliente, reconheça calorosamente e use o nome durante toda a conversa.",
                "Lembre-se das preferências dos clientes e consultas anteriores usando os nomes deles.",
                "Se não conseguir atender uma solicitação, ofereça educadamente para conectá-los com um membro da equipe.",
                "Seja conversacional e use um tom caloroso e acolhedor nas suas respostas.",
                "Todos os preços devem ser apresentados em EUR (euros)."
            ],
            storage=SqliteStorage(
                table_name="salon_agent_sessions",
                db_file="salon_agent_data.db",
                auto_upgrade_schema=True
            ),
            memory=Memory(
                model=self.xai_model,
                db=SqliteMemoryDb(
                    db_file="salon_memory.db",
                    table_name="user_memories"
                )
            ),
            enable_agentic_memory=True,
            enable_user_memories=True,
            add_history_to_messages=True,
            num_history_runs=3,
            show_tool_calls=True,
            markdown=True,
        )
        
        # Load salon services
        self.services = self._load_services()
        
    def _load_services(self) -> List[Dict]:
        """Load available services from database"""
        services = self.session.query(Service).filter_by(active=True).all()
        return [
            {
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "duration": service.duration_minutes,
                "price": service.price
            }
            for service in services
        ]
    
    def get_or_create_client(self, phone: str, name: Optional[str] = None) -> Client:
        """Get existing client or create new one"""
        client = self.session.query(Client).filter_by(phone=phone).first()
        
        if not client:
            client = Client(
                phone=phone,
                name=name,
                created_at=datetime.now(timezone.utc)
            )
            self.session.add(client)
            self.session.commit()
            
        return client
    
    def check_availability(self, date: datetime, duration_minutes: int) -> List[datetime]:
        """Check available time slots for a given date and duration"""
        # Simple availability check - assume 9AM to 7PM, every 15 minutes
        # In a real system, this would check against existing appointments and staff schedules
        
        start_hour = 9  # 9 AM
        end_hour = 19   # 7 PM
        slot_interval = 15  # 15 minute intervals
        
        available_slots = []
        current_time = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end_time = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        while current_time + timedelta(minutes=duration_minutes) <= end_time:
            # Check if this slot conflicts with existing appointments
            conflict = self.session.query(Appointment).filter(
                Appointment.appointment_datetime <= current_time,
                Appointment.appointment_datetime + timedelta(minutes=Appointment.duration_minutes) > current_time,
                Appointment.status.in_(['scheduled', 'confirmed'])
            ).first()
            
            if not conflict:
                available_slots.append(current_time)
            
            current_time += timedelta(minutes=slot_interval)
            
        return available_slots[:10]  # Return first 10 available slots
    
    def book_appointment(self, client_id: int, service_id: int, appointment_datetime: datetime, notes: str = "") -> Dict:
        """Book an appointment for a client"""
        try:
            service = self.session.query(Service).get(service_id)
            if not service:
                return {"success": False, "message": "Service not found"}
            
            # Check if the time slot is still available
            conflict = self.session.query(Appointment).filter(
                Appointment.appointment_datetime <= appointment_datetime,
                Appointment.appointment_datetime + timedelta(minutes=service.duration_minutes) > appointment_datetime,
                Appointment.status.in_(['scheduled', 'confirmed'])
            ).first()
            
            if conflict:
                return {"success": False, "message": "Time slot is no longer available"}
            
            # Create the appointment
            appointment = Appointment(
                client_id=client_id,
                service_id=service_id,
                appointment_datetime=appointment_datetime,
                duration_minutes=service.duration_minutes,
                status='scheduled',
                notes=notes
            )
            
            self.session.add(appointment)
            self.session.commit()
            
            return {
                "success": True, 
                "appointment_id": appointment.id,
                "message": f"Appointment booked successfully for {appointment_datetime.strftime('%B %d, %Y at %I:%M %p')}"
            }
            
        except Exception as e:
            self.session.rollback()
            return {"success": False, "message": f"Booking failed: {str(e)}"}
    
    def update_client_name(self, phone: str, name: str) -> Dict:
        """Update client name in database"""
        try:
            client = self.session.query(Client).filter_by(phone=phone).first()
            if client:
                client.name = name
                self.session.commit()
                return {"success": True, "message": f"Updated name for {phone} to {name}"}
            else:
                return {"success": False, "message": "Client not found"}
        except Exception as e:
            self.session.rollback()
            return {"success": False, "message": f"Error updating name: {str(e)}"}
    
    def get_services_info(self) -> str:
        """Get formatted services information"""
        services_text = "Our Services:\n\n"
        for service in self.services:
            services_text += f"• {service['name']} - ${service['price']:.2f}\n"
            services_text += f"  {service['description']} ({service['duration']} minutes)\n\n"
        return services_text
    
    def process_message(self, phone: str, message: str, user_name: Optional[str] = None) -> str:
        """
        Process incoming SMS message using Agno's workflow capabilities
        """
        # Create or get client
        client = self.get_or_create_client(phone, user_name)
        
        # Set user context for Agno memory system
        self.user_id = phone
        self.session_id = f"{phone}_{datetime.now().strftime('%Y%m%d')}"
        
        # Create context for the agent
        has_name = bool(client.name)
        context = {
            "client_phone": phone,
            "client_name": client.name if has_name else None,
            "has_name": has_name,
            "salon_name": os.getenv("SALON_NAME", "Elegant Nails Spa"),
            "salon_hours": os.getenv("SALON_HOURS", "Mon-Sat 9AM-7PM, Sun 11AM-5PM"),
            "services": self.services,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add context to agent instructions for this conversation
        name_instruction = ""
        if not has_name:
            name_instruction = """
        IMPORTANTE: Este cliente ainda não tem nome no nosso sistema. 
        Pergunte o nome dele educadamente no início da conversa e lembre-se de usá-lo.
        Quando fornecerem o nome, reconheça calorosamente.
        """
        else:
            name_instruction = f"""
        Nome do cliente: {client.name} - Use o nome durante toda a conversa.
        """
        
        contextual_instructions = f"""
        Contexto atual:
        - Telefone do cliente: {context['client_phone']}
        {name_instruction}
        - Salão: {context['salon_name']}
        - Horários: {context['salon_hours']}
        - Hora atual: {context['current_time']}
        
        Serviços disponíveis: {json.dumps(context['services'], indent=2)}
        
        Para marcação de consulta:
        1. Descubra qual serviço querem
        2. Sugira horários disponíveis
        3. Confirme os detalhes da consulta
        4. Marque a consulta quando confirmada
        
        IMPORTANTE: Responda sempre em português! Seja conversacional e prestativa!
        Preços são sempre em EUR (euros).
        """
        
        # Use Agno's built-in conversation handling
        response = self.run(
            message + f"\n\nContext: {contextual_instructions}",
            stream=False
        )
        
        return response.content

# Global receptionist instance (created lazily)
_receptionist = None

def process_sms(phone: str, message: str, user_name: Optional[str] = None) -> str:
    """
    Main entry point for processing SMS messages
    """
    global _receptionist
    if _receptionist is None:
        _receptionist = SalonReceptionist()
    return _receptionist.process_message(phone, message, user_name)