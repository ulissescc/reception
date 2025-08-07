"""
Database models for the nail salon receptionist system
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

Base = declarative_base()

class Client(Base):
    """Client information table"""
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    name = Column(String(100))
    email = Column(String(100))
    preferences = Column(Text)  # JSON string for client preferences
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to appointments
    appointments = relationship("Appointment", back_populates="client")

class Service(Base):
    """Available services table"""
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    active = Column(Boolean, default=True)
    
    # Relationship to appointments
    appointments = relationship("Appointment", back_populates="service")

class Appointment(Base):
    """Appointments table"""
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    appointment_datetime = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    status = Column(String(20), default='scheduled')  # scheduled, completed, cancelled, no_show
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", back_populates="appointments")
    service = relationship("Service", back_populates="appointments")

class AvailabilitySlot(Base):
    """Available time slots table"""
    __tablename__ = 'availability_slots'
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    is_available = Column(Boolean, default=True)
    staff_member = Column(String(50))

def init_database():
    """Initialize the database with default data"""
    
    # Create database engine
    database_url = os.getenv('DATABASE_URL', 'sqlite:///salon_data.db')
    engine = create_engine(database_url, echo=False)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Add default services if they don't exist (Portuguese with EUR prices)
    default_services = [
        {"name": "Manicure Básica", "description": "Manicure clássica com verniz", "duration_minutes": 45, "price": 23.00},
        {"name": "Manicure em Gel", "description": "Manicure com verniz gel de longa duração", "duration_minutes": 60, "price": 32.00},
        {"name": "Pedicure Básica", "description": "Pedicure clássica com verniz", "duration_minutes": 60, "price": 28.00},
        {"name": "Pedicure em Gel", "description": "Pedicure com verniz gel de longa duração", "duration_minutes": 75, "price": 37.00},
        {"name": "Nail Art", "description": "Design personalizado de nail art", "duration_minutes": 90, "price": 46.00},
        {"name": "Unhas de Acrílico - Conjunto Completo", "description": "Conjunto completo de unhas de acrílico", "duration_minutes": 120, "price": 55.00},
        {"name": "Preenchimento de Acrílico", "description": "Preenchimento de unhas de acrílico", "duration_minutes": 90, "price": 37.00}
    ]
    
    # Check if services already exist
    if session.query(Service).count() == 0:
        for service_data in default_services:
            service = Service(**service_data)
            session.add(service)
        session.commit()
        print("Added default services to database")
    
    session.close()
    return engine

if __name__ == "__main__":
    # Initialize database when run directly
    engine = init_database()
    print("Database initialized successfully!")