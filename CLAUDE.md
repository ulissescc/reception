# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered nail salon receptionist system built with the Agno framework using xAI's Grok model. The system implements a Level 5 agentic workflow that handles SMS messages from clients, manages appointments, and maintains client information using persistent storage and memory.

## Architecture

### Core Components

- **receptionist.py**: Main Agno agent implementing `SalonReceptionist` class with built-in memory and SQLite storage
- **database.py**: SQLAlchemy models and database initialization with default services
- **main.py**: Entry point with `process_sms_message()` function for SMS processing
- **demo.py**: Interactive demonstration script showing conversation flows
- **test_xai.py**: xAI Grok model integration testing suite

### Agno Framework Integration

- **xAI Grok Model**: Uses `grok-3` model (configured in `receptionist.py:37`)
- **Level 5 Agentic Workflow**: State persistence with deterministic execution patterns
- **Built-in SQLite Storage**: Agent session storage via `SqliteStorage` (salon_agent_data.db)
- **Agent Memory**: Automatic user memory and session summaries with `AgentMemory`
- **Multi-user Support**: Per-phone-number client contexts with individual session IDs
- **Database Layer**: Separate business data storage (salon_data.db) from agent storage

### Database Architecture

- **Clients Table**: Phone numbers as unique identifiers, names, preferences, timestamps
- **Services Table**: Default salon services with pricing, duration, and descriptions
- **Appointments Table**: Booking records with foreign keys to clients and services
- **Availability Table**: Basic time slot management (9AM-7PM with 15-minute intervals)
- **Dual Storage**: Business data (salon_data.db) + agent sessions (salon_agent_data.db)

## Development Commands

### Setup Environment
```bash
# Create and activate virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env  # Edit with XAI_API_KEY
```

### Database Operations
```bash
# Initialize database with default services
python database.py

# Reset all data (removes both databases)
rm salon_data.db salon_agent_data.db salon_memory.db
python database.py
```

### Running the System
```bash
# Run main test suite with sample conversations
python main.py

# Interactive demo with conversation flows
python demo.py

# Test xAI Grok integration
python test_xai.py

# Use as SMS processor programmatically
python -c "from main import process_sms_message; print(process_sms_message('+1234567890', 'I need a manicure', 'Sarah'))"
```

### Testing and Debugging
```bash
# Test individual components
python -c "from receptionist import SalonReceptionist; r = SalonReceptionist(); print('Receptionist initialized')"

# Check database contents
sqlite3 salon_data.db "SELECT * FROM services;"
sqlite3 salon_data.db "SELECT * FROM clients;"
sqlite3 salon_data.db "SELECT * FROM appointments;"
```

## Key Features Implemented

### Client Management
- Automatic client creation from phone numbers
- Persistent client preferences and history
- Multi-session conversation memory

### Appointment Booking
- Service selection with pricing information
- Availability checking (basic 9AM-7PM schedule)
- Appointment confirmation and storage
- Conflict prevention for double-booking

### Conversation Handling
- Natural language processing for booking requests
- Context-aware responses using Agno's memory system
- Service information and hours inquiries
- Error handling with graceful fallbacks

## Integration Points

### SMS Input Processing
The system expects SMS messages as input via the `process_sms_message()` function:
- `phone_number`: Client's phone number (string)
- `message`: SMS message content (string)  
- `user_name`: Optional client name (string)

### Database Integration
- SQLAlchemy ORM for all database operations
- Automatic schema creation and migration
- Transaction handling with rollback on errors

## Configuration

### Environment Variables
- `XAI_API_KEY`: **Required** for xAI Grok model functionality
- `DATABASE_URL`: SQLite database path (defaults to 'sqlite:///salon_data.db')
- `SALON_NAME`: Salon name for responses (defaults to 'Elegant Nails Spa')
- `SALON_PHONE`: Fallback phone number for errors (defaults to '(555) 123-4567')
- `SALON_HOURS`: Operating hours information (defaults to 'Mon-Sat 9AM-7PM, Sun 11AM-5PM')

### Default Services
System initializes with standard nail salon services:
- Basic/Gel Manicures and Pedicures
- Nail Art and Acrylic services
- Pricing from $25-60 with realistic durations

## Key Implementation Details

### Agent Session Management
- Global singleton pattern for `SalonReceptionist` instance (`receptionist.py:222-231`)
- Session IDs use format: `{phone}_{YYYYMMDD}` for daily session grouping
- User ID equals phone number for consistent client identification

### Database Transaction Handling
- SQLAlchemy sessions with explicit rollback on appointment booking failures
- Separate database connections for business data vs agent storage
- Automatic schema creation and default service population

### Availability Algorithm
- Simple time slot checking: 9AM-7PM in 15-minute intervals
- Conflict detection via appointment overlap queries
- Returns first 10 available slots for user selection

### Memory and Context
- Agno's `AgentMemory` with user memories and session summaries configured
- **Note**: Current implementation uses `MemoryDb` instead of recommended `SqliteMemoryDb`
- **Note**: Missing auto-update parameters (`update_user_memories_after_run`, `update_session_summary_after_run`)
- Context injection includes client info, services, and current time
- User ID set per conversation (phone number) for memory persistence
- JSON-formatted service data passed to agent for booking logic

### Error Handling Patterns
- Try-catch blocks with fallback to salon phone number
- Database rollbacks on booking conflicts or errors
- Graceful degradation when agent initialization fails