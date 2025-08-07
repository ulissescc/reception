#!/usr/bin/env python3
"""
FastAPI Web Chat Server for Nail Salon AI Receptionist
"""

import os
import uuid
import json
import httpx
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from receptionist import SalonReceptionist

# Load environment variables
load_dotenv()

# Set OpenAI key to xAI for memory compatibility
os.environ["OPENAI_API_KEY"] = os.getenv("XAI_API_KEY", "")

# Initialize FastAPI app
app = FastAPI(title="Nail Salon AI Receptionist Chat", version="1.0.0")

# Global receptionist instance
receptionist = None

def get_receptionist():
    """Get or create the salon receptionist instance"""
    global receptionist
    if receptionist is None:
        receptionist = SalonReceptionist()
    return receptionist

# Request/Response models for webhook (realistic SMS structure)
class WebhookMessage(BaseModel):
    phone_number: str  # Required - always provided by SMS webhook
    message: str       # Required - the SMS content

# WhatsApp Z-API webhook structure
class WhatsAppText(BaseModel):
    message: str

class WhatsAppWebhook(BaseModel):
    isStatusReply: bool
    chatLid: str
    connectedPhone: str
    waitingMessage: bool
    isEdit: bool
    isGroup: bool
    isNewsletter: bool
    instanceId: str
    messageId: str
    phone: str
    fromMe: bool
    momment: int
    status: str
    chatName: str
    senderPhoto: Optional[str]
    senderName: str
    photo: Optional[str]
    broadcast: bool
    participantLid: Optional[str]
    forwarded: bool
    type: str
    fromApi: bool
    text: Optional[WhatsAppText]

# Internal chat message (for web interface testing)
class ChatMessage(BaseModel):
    message: str
    user_name: Optional[str] = None
    phone_number: Optional[str] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    user_name: Optional[str] = None

@app.get("/simple", response_class=HTMLResponse)
async def simple_chat_interface():
    """Serve a simpler chat interface"""
    with open("simple_chat.html", "r") as f:
        return f.read()

@app.get("/", response_class=HTMLResponse)
async def chat_interface():
    """Serve the chat interface HTML page"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>💅 Elegant Nails Spa - AI Receptionist</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                height: 100vh;
                display: flex;
                flex-direction: column;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                text-align: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header h1 {
                margin: 0;
                font-size: 2em;
            }
            .header p {
                margin: 5px 0 0 0;
                opacity: 0.9;
            }
            .chat-container {
                flex: 1;
                display: flex;
                flex-direction: column;
                max-width: 800px;
                margin: 0 auto;
                width: 100%;
                padding: 20px;
                box-sizing: border-box;
            }
            .user-info {
                background: white;
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                display: flex;
                gap: 10px;
                align-items: center;
            }
            .user-info input {
                padding: 8px 12px;
                border: 2px solid #e1e5e9;
                border-radius: 6px;
                font-size: 14px;
            }
            .user-info input:focus {
                outline: none;
                border-color: #667eea;
            }
            .chat-messages {
                flex: 1;
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
                overflow-y: auto;
                max-height: 400px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }
            .message {
                margin-bottom: 15px;
                padding: 12px 16px;
                border-radius: 18px;
                max-width: 70%;
                word-wrap: break-word;
            }
            .user-message {
                background: #667eea;
                color: white;
                margin-left: auto;
                text-align: right;
            }
            .bot-message {
                background: #f1f3f4;
                color: #333;
                margin-right: auto;
            }
            .message-time {
                font-size: 11px;
                opacity: 0.7;
                margin-top: 5px;
            }
            .input-area {
                display: flex;
                gap: 10px;
                background: white;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            }
            #messageInput {
                flex: 1;
                padding: 12px;
                border: 2px solid #e1e5e9;
                border-radius: 25px;
                font-size: 16px;
                outline: none;
            }
            #messageInput:focus {
                border-color: #667eea;
            }
            #sendButton {
                padding: 12px 24px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-weight: bold;
                transition: background 0.3s;
            }
            #sendButton:hover {
                background: #5a6fd8;
            }
            #sendButton:disabled {
                background: #ccc;
                cursor: not-allowed;
            }
            .loading {
                display: none;
                color: #667eea;
                font-style: italic;
                padding: 10px;
            }
            .error {
                background: #ffebee;
                color: #c62828;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                display: none;
            }
            .typing-cursor {
                animation: blink 1s infinite;
                color: #667eea;
            }
            @keyframes blink {
                0%, 50% { opacity: 1; }
                51%, 100% { opacity: 0; }
            }
            .streaming-content {
                min-height: 1em;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>💅 Elegant Nails Spa</h1>
            <p>AI-Powered Receptionist - Book Your Appointment Today!</p>
        </div>
        
        <div class="chat-container">
            <div class="user-info">
                <label>Seu Telefone:</label>
                <input type="text" id="phoneNumber" placeholder="+351-912-345-678" value="+351-912-345-678">
                <small style="color: #666; font-size: 12px;">Simulador de SMS - Apenas o número é enviado (como SMS real)</small>
            </div>
            
            <div class="chat-messages" id="chatMessages">
                <div class="message bot-message">
                    <div>Olá! Bem-vindo ao Elegant Nails Spa! 💅 Sou a sua recepcionista AI. Como posso ajudar hoje?</div>
                    <div class="message-time">Agora</div>
                </div>
            </div>
            
            <div class="loading" id="loading">AI está a escrever...</div>
            <div class="error" id="error"></div>
            
            <div class="input-area">
                <input type="text" id="messageInput" placeholder="Escreva a sua mensagem aqui..." />
                <button id="sendButton" onclick="sendMessage()">Enviar</button>
            </div>
        </div>

        <script>
            let sessionId = Math.random().toString(36).substring(7);
            
            function getCurrentTime() {
                return new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            }
            
            function addMessage(message, isUser = false) {
                const chatMessages = document.getElementById('chatMessages');
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message ' + (isUser ? 'user-message' : 'bot-message');
                
                messageDiv.innerHTML = `
                    <div>${message}</div>
                    <div class="message-time">${getCurrentTime()}</div>
                `;
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
            
            async function sendMessage() {
                const messageInput = document.getElementById('messageInput');
                const sendButton = document.getElementById('sendButton');
                const loading = document.getElementById('loading');
                const error = document.getElementById('error');
                const phoneNumber = document.getElementById('phoneNumber').value.trim();
                
                const message = messageInput.value.trim();
                if (!message) return;
                
                if (!phoneNumber) {
                    error.textContent = 'Por favor, insira o seu número de telefone.';
                    error.style.display = 'block';
                    return;
                }
                
                // Add user message to chat (SMS-style)
                addMessage(message, true);
                
                // Clear input and disable button
                messageInput.value = '';
                sendButton.disabled = true;
                loading.style.display = 'block';
                error.style.display = 'none';
                
                try {
                    // Use webhook SMS endpoint (realistic SMS simulation)
                    const response = await fetch('/webhook/sms', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            phone_number: phoneNumber,
                            message: message
                        })
                    });
                    
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    
                    const data = await response.json();
                    
                    // Add bot response to chat (SMS-style)
                    loading.style.display = 'none';
                    addMessage(formatMessage(data.response));
                    
                } catch (err) {
                    console.error('Error:', err);
                    loading.style.display = 'none';
                    error.textContent = 'Desculpe, ocorreu um erro ao processar a sua mensagem. Tente novamente.';
                    error.style.display = 'block';
                }
                
                // Re-enable button and hide loading
                sendButton.disabled = false;
                loading.style.display = 'none';
                messageInput.focus();
            }
            
            function formatMessage(text) {
                // Simple text formatting - just replace newlines
                return text.replace(/\\n/g, '<br>');
            }
            
            // Send message on Enter key
            document.getElementById('messageInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });
            
            // Focus on input when page loads
            window.onload = function() {
                document.getElementById('messageInput').focus();
            };
        </script>
    </body>
    </html>
    """

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(chat_message: ChatMessage):
    """Handle chat messages from the web interface (non-streaming)"""
    try:
        # Get receptionist instance
        salon_receptionist = get_receptionist()
        
        # Use provided phone number or generate session-based one
        phone_number = chat_message.phone_number or f"+1555{chat_message.session_id or uuid.uuid4().hex[:6]}"
        
        # Process the message (non-streaming)
        response = salon_receptionist.process_message(
            phone=phone_number,
            message=chat_message.message,
            user_name=chat_message.user_name
        )
        
        # Generate session ID if not provided
        session_id = chat_message.session_id or str(uuid.uuid4())
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            user_name=chat_message.user_name
        )
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.post("/chat/stream")
async def chat_stream_endpoint(chat_message: ChatMessage):
    """Handle streaming chat messages using Server-Sent Events"""
    
    def generate_stream():
        try:
            # Get receptionist instance
            salon_receptionist = get_receptionist()
            
            # Use provided phone number or generate session-based one
            phone_number = chat_message.phone_number or f"+1555{chat_message.session_id or uuid.uuid4().hex[:6]}"
            
            # Generate session ID if not provided
            session_id = chat_message.session_id or str(uuid.uuid4())
            
            # Session management is now handled in process_message method
            # Create or get client
            client = salon_receptionist.get_or_create_client(phone_number, chat_message.user_name)
            
            # Create context for the agent
            context = {
                "client_phone": phone_number,
                "client_name": client.name or "valued client",
                "salon_name": os.getenv("SALON_NAME", "Elegant Nails Spa"),
                "salon_hours": os.getenv("SALON_HOURS", "Mon-Sat 9AM-7PM, Sun 11AM-5PM"),
                "services": salon_receptionist.services,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Add context to agent instructions for this conversation
            contextual_instructions = f"""
            Current context:
            - Client phone: {context['client_phone']}
            - Client name: {context['client_name']}
            - Salon: {context['salon_name']}
            - Hours: {context['salon_hours']}
            - Current time: {context['current_time']}
            
            Available services: {json.dumps(context['services'], indent=2)}
            
            For appointment booking:
            1. Get the service they want
            2. Suggest available time slots
            3. Confirm the appointment details
            4. Book the appointment when confirmed
            
            Be conversational and helpful!
            """
            
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id, 'timestamp': datetime.now().isoformat()})}\n\n"
            
            # Use Agno's built-in streaming capability
            response = salon_receptionist.run(
                chat_message.message + f"\n\nContext: {contextual_instructions}",
                stream=True
            )
            
            # Stream the response
            for chunk in response:
                if hasattr(chunk, 'content') and chunk.content:
                    data = {
                        'type': 'content',
                        'content': chunk.content,
                        'session_id': session_id,
                        'timestamp': datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(data)}\n\n"
            
            # Send completion signal
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
            
        except Exception as e:
            error_data = {
                'type': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@app.post("/webhook/sms")
async def webhook_sms_endpoint(webhook_message: WebhookMessage):
    """Handle SMS webhook - only receives phone and message"""
    try:
        # Get receptionist instance
        salon_receptionist = get_receptionist()
        
        # Process the message without a user name (will be asked by agent)
        response = salon_receptionist.process_message(
            phone=webhook_message.phone_number,
            message=webhook_message.message,
            user_name=None  # No name provided - agent will ask
        )
        
        return {
            "response": response,
            "phone_number": webhook_message.phone_number,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Webhook SMS error: {str(e)}")
        # Return a fallback message for SMS
        return {
            "response": f"I apologize, but I'm experiencing technical difficulties. Please call us directly at {os.getenv('SALON_PHONE', '(555) 123-4567')} or try again in a moment.",
            "phone_number": webhook_message.phone_number,
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.post("/webhook/whatsapp")
@app.post("/webhook/whatsapp/")
async def whatsapp_webhook_endpoint(webhook_data: WhatsAppWebhook):
    """Handle WhatsApp Z-API webhook messages"""
    try:
        print("=" * 60)
        print("📱 WHATSAPP WEBHOOK DATA:")
        print("=" * 60)
        print(f"📞 From: {webhook_data.phone} ({webhook_data.senderName})")
        print(f"💬 Message: {webhook_data.text.message if webhook_data.text else 'No text'}")
        print(f"📋 Type: {webhook_data.type}")
        print(f"🔄 From Me: {webhook_data.fromMe}")
        print("=" * 60)
        
        # Process only received text messages (not status updates, etc.)
        if (webhook_data.type == "ReceivedCallback" and 
            webhook_data.text and 
            webhook_data.text.message and 
            not webhook_data.fromMe):
            
            phone = webhook_data.phone
            message = webhook_data.text.message
            
            print(f"📞 Processing message from {phone}: \"{message}\"")
            
            # Get receptionist instance and process message
            salon_receptionist = get_receptionist()
            
            # Process the message (Portuguese receptionist) - don't use webhook name
            ai_response = salon_receptionist.process_message(
                phone=phone,
                message=message,
                user_name=None  # Don't use webhook name - let AI ask for name
            )
            
            print(f"🤖 AI Response: \"{ai_response}\"")
            
            # Send response back via Z-API
            z_api_url = f"https://api.z-api.io/instances/{webhook_data.instanceId}/token/14BDD904C38209CB129D97A7/send-text"
            
            async with httpx.AsyncClient() as client:
                z_api_response = await client.post(
                    z_api_url,
                    json={
                        "phone": phone,
                        "message": ai_response
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Client-Token": "Fbb71b79c5fbe4568ad040a6d609bd5f2S"
                    },
                    timeout=10.0
                )
                
                if z_api_response.status_code == 200:
                    print(f"✅ Response sent successfully to {phone}")
                else:
                    print(f"❌ Failed to send Z-API response: {z_api_response.status_code} - {z_api_response.text}")
        
        return {"status": "received", "processed": webhook_data.type == "ReceivedCallback"}
        
    except Exception as e:
        print(f"❌ Error processing WhatsApp webhook: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nail_salon_receptionist"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Nail Salon AI Receptionist Chat Server...")
    print("📱 Open http://localhost:8000 to start chatting!")
    print("🔄 Server starting with xAI Grok integration...")
    uvicorn.run(app, host="0.0.0.0", port=8000)