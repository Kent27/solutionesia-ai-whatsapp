# Solutionesia AI WhatsApp - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Core Features](#core-features)
5. [Code Flow](#code-flow)
6. [API Endpoints](#api-endpoints)
7. [Services & Components](#services--components)
8. [Database & Storage](#database--storage)
9. [Authentication](#authentication)
10. [Deployment](#deployment)

---

## Overview

**Solutionesia AI WhatsApp** is a FastAPI-based application that provides AI-powered document generation, WhatsApp chatbot integration, and OpenAI Assistant API management. The application serves as a comprehensive platform for:

- **Document Generation**: Create Word documents from JSON data using templates
- **WhatsApp Integration**: AI-powered chatbot that processes messages and images via WhatsApp Business API
- **OpenAI Assistant Management**: Create and manage AI assistants with function calling capabilities
- **Contact Management**: Track customers and conversations in Google Sheets and MariaDB
- **Action System**: Register and execute custom functions/APIs as OpenAI tools

---

## Architecture

The application follows a **layered architecture** pattern:

```
┌─────────────────────────────────────────┐
│         FastAPI Application            │
│         (app/main.py)                   │
└─────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼────┐ ┌───▼────┐ ┌───▼────┐
│  Routers   │ │Services│ │ Models │
│            │ │        │ │        │
│ - auth     │ │- OpenAI│ │- Pydantic│
│ - assistant│ │- WhatsApp│ │- Data│
│ - whatsapp │ │- Action│ │  Models│
│ - contact  │ │- Auth  │ │        │
└────────────┘ └────────┘ └────────┘
        │           │           │
        └───────────┼───────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼────┐ ┌───▼────┐ ┌───▼────┐
│  External  │ │Database│ │ Utils │
│   APIs     │ │        │ │        │
│            │ │- MariaDB│ │- Logging│
│- OpenAI    │ │- Sheets│ │- Auth │
│- WhatsApp  │ │        │ │- Sheets│
└────────────┘ └────────┘ └────────┘
```

### Key Design Patterns:
- **Dependency Injection**: Services are injected via FastAPI's `Depends()`
- **Singleton Pattern**: ActionService uses singleton for action registry
- **Service Layer**: Business logic separated from routing
- **Async/Await**: Full async support for I/O operations

---

## Project Structure

```
solutionesia-ai-whatsapp/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── routers/                # API route handlers
│   │   ├── assistant_router.py # OpenAI Assistant endpoints
│   │   ├── whatsapp.py         # WhatsApp webhook handlers
│   │   ├── whatsapp_api.py     # WhatsApp API endpoints
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── contact.py           # Contact management
│   │   ├── message.py           # Message management
│   │   └── label.py             # Label management
│   ├── services/               # Business logic layer
│   │   ├── openai_service.py   # OpenAI Assistant API wrapper
│   │   ├── whatsapp_service.py # WhatsApp Business API integration
│   │   ├── action_service.py   # Action/tool registration system
│   │   ├── auth_service.py     # User authentication
│   │   ├── contact_service.py # Contact CRUD operations
│   │   ├── document_service.py # Document generation
│   │   └── ai_service.py       # AI text processing
│   ├── models/                 # Pydantic data models
│   │   ├── assistant_models.py # Assistant-related models
│   │   ├── whatsapp_models.py  # WhatsApp webhook models
│   │   ├── auth_models.py      # Authentication models
│   │   └── ...
│   ├── utils/                  # Utility functions
│   │   ├── google_sheets.py    # Google Sheets integration
│   │   ├── app_logger.py       # Logging configuration
│   │   ├── auth_utils.py       # JWT token handling
│   │   └── logging_utils.py     # WhatsApp message logging
│   ├── database/               # Database configuration
│   │   ├── mysql.py            # MariaDB connection pool
│   │   └── migrations/         # SQL migration scripts
│   ├── functions/              # Custom function implementations
│   │   ├── chat_functions.py   # Chat-related functions
│   │   ├── menu_functions.py   # Menu-related functions
│   │   ├── employee_functions.py
│   │   └── loyalty_functions.py
│   ├── backup/                 # Deprecated code (ManyChat)
│   │   ├── manychat_models.py
│   │   └── manychat_service.py
│   └── static/                 # Static files
│       ├── templates/          # Document templates
│       └── generated_docs/     # Generated documents
├── config/                     # Configuration files
│   └── credentials/            # Service account keys
├── tests/                      # Test files
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker image definition
└── environment.yml             # Conda environment specification
```

---

## Core Features

### 1. OpenAI Assistant Management
- Create, update, and manage AI assistants
- Thread-based conversation management
- Function calling with custom actions
- Support for text and image content

### 2. WhatsApp Chatbot
- Webhook integration with WhatsApp Business API
- AI-powered message processing
- Image processing with OpenAI Vision
- Customer management and conversation tracking
- Live Chat mode (bypasses AI for human agents)

### 3. Document Generation
- Generate Word documents from JSON data
- Template-based document creation
- Text-to-document conversion using AI

### 4. Action System
- Register custom functions as OpenAI tools
- Support for local Python functions and remote API calls
- Dynamic function execution during assistant runs

### 5. Contact Management
- Dual storage: Google Sheets + MariaDB
- Customer tracking with phone numbers
- Thread ID management for conversations
- Chat status management

---

## Code Flow

### 1. WhatsApp Message Processing Flow

```
WhatsApp Webhook Request
    │
    ├─► Verify Webhook (GET /whatsapp/webhook)
    │   └─► Return challenge if valid
    │
    └─► Process Message (POST /whatsapp/webhook)
        │
        ├─► Validate timestamp (reject if >24h old)
        ├─► Check for duplicate messages (MessageCache)
        ├─► Log incoming message
        │
        ├─► Check Customer in Google Sheets
        │   ├─► If not exists: Create customer record
        │   └─► If exists: Update if needed
        │
        ├─► Check Customer in MariaDB Contacts
        │   ├─► If not exists: Create contact record
        │   └─► If exists: Update name if changed
        │
        ├─► Check Chat Status
        │   ├─► If "Live Chat": Skip AI processing
        │   └─► If normal: Continue to AI
        │
        ├─► Process Message Content
        │   ├─► Text messages: Add as text content
        │   └─► Image messages:
        │       ├─► Download image from WhatsApp
        │       ├─► Upload to OpenAI Files API
        │       └─► Add as image_file content
        │
        ├─► Call OpenAI Assistant
        │   ├─► Create/retrieve thread
        │   ├─► Add message with content
        │   ├─► Run assistant
        │   ├─► Handle function calls (if any)
        │   └─► Get assistant response
        │
        ├─► Update Thread ID
        │   ├─► Update in Google Sheets
        │   └─► Update in MariaDB
        │
        └─► Send Response via WhatsApp API
            └─► Log outgoing message
```

### 2. OpenAI Assistant Chat Flow

```
Chat Request (POST /assistant/chat)
    │
    ├─► OpenAIAssistantService.chat()
    │   │
    │   ├─► Create or use existing thread
    │   │   └─► client.beta.threads.create()
    │   │
    │   ├─► Parse message content
    │   │   └─► Handle JSON strings or direct content
    │   │
    │   ├─► Add user message to thread
    │   │   └─► client.beta.threads.messages.create()
    │   │
    │   ├─► Run assistant
    │   │   └─► client.beta.threads.runs.create()
    │   │
    │   ├─► Poll for completion
    │   │   ├─► Check run status
    │   │   │   └─► client.beta.threads.runs.retrieve()
    │   │   │
    │   │   └─► If status == "requires_action":
    │   │       ├─► Extract tool calls
    │   │       ├─► Execute functions via ActionService
    │   │       ├─► Submit tool outputs
    │   │       │   └─► client.beta.threads.runs.submit_tool_outputs()
    │   │       └─► Continue polling
    │   │
    │   └─► Retrieve messages
    │       └─► client.beta.threads.messages.list()
    │
    └─► Return ChatResponse with messages
```

### 3. Function Calling Flow

```
Assistant Run with Function Call
    │
    ├─► Assistant decides to call function
    │   └─► Run status becomes "requires_action"
    │
    ├─► Extract tool calls from run
    │   └─► run_status.required_action.submit_tool_outputs.tool_calls
    │
    ├─► For each tool call:
    │   ├─► Get function name and arguments
    │   ├─► Look up function in actions.json
    │   ├─► Determine if local or remote
    │   │
    │   ├─► If local function:
    │   │   ├─► Import module dynamically
    │   │   ├─► Get function reference
    │   │   └─► Execute function with arguments
    │   │
    │   └─► If remote API:
    │       ├─► Build HTTP request
    │       ├─► Add authentication headers
    │       └─► Make API call
    │
    ├─► Collect all tool outputs
    │   └─► Format as [{tool_call_id, output}, ...]
    │
    ├─► Submit tool outputs to OpenAI
    │   └─► client.beta.threads.runs.submit_tool_outputs()
    │
    └─► Continue polling until completed
```

### 4. Document Generation Flow

```
Document Generation Request (POST /generate-doc)
    │
    ├─► Receive JSON data + optional template
    │   └─► If no template: Load default template1.docx
    │
    ├─► Decode base64 template
    │   └─► Convert to BytesIO object
    │
    ├─► DocumentService.generate_document()
    │   ├─► Load template using python-docx
    │   ├─► Process JSON data
    │   ├─► Replace placeholders in template
    │   └─► Save generated document
    │
    └─► Return download URL
        └─► GET /download/{filename} serves the file
```

---

## API Endpoints

### Assistant Endpoints (`/assistant`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/create` | Create a new OpenAI assistant |
| POST | `/thread` | Create a new conversation thread |
| POST | `/message/{thread_id}` | Add a message to a thread |
| POST | `/run/{assistant_id}/{thread_id}` | Run assistant on a thread |
| GET | `/run/{thread_id}/{run_id}/status` | Get run status |
| GET | `/run/{thread_id}/{run_id}/wait` | Wait for run completion |
| POST | `/run/{thread_id}/{run_id}/expire` | Cancel/expire a run |
| GET | `/messages/{thread_id}` | Get thread messages |
| POST | `/chat` | Simplified chat endpoint (handles full flow) |
| PATCH | `/assistants/{assistant_id}` | Update assistant configuration |
| POST | `/actions/register` | Register a new action/function |
| GET | `/actions` | List all registered actions |

### WhatsApp Endpoints (`/whatsapp`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/webhook` | Verify webhook (WhatsApp challenge) |
| POST | `/webhook` | Receive WhatsApp messages |
| POST | `/set-chat-status` | Set customer chat status (Live Chat mode) |

### Authentication Endpoints (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Authenticate user and get JWT token |
| POST | `/register` | Register a new user |

### Document Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/generate-doc` | Generate document from JSON + template |
| GET | `/download/{filename}` | Download generated document |
| POST | `/text-to-doc` | Convert text/docx to JSON then generate document |
| POST | `/analyze-api` | Analyze API structure |

---

## Services & Components

### OpenAIAssistantService
**Location**: `app/services/openai_service.py`

**Purpose**: Wrapper around OpenAI Assistant API

**Key Methods**:
- `create_assistant()`: Create new assistant
- `create_thread()`: Create conversation thread
- `add_message()`: Add message to thread
- `run_assistant()`: Execute assistant run
- `chat()`: Complete chat flow with function calling
- `get_messages()`: Retrieve thread messages
- `get_run_status()`: Check run status
- `wait_for_completion()`: Poll until run completes

**Async Pattern**: Uses `_run_sync()` to wrap synchronous OpenAI calls in thread pool executor

### WhatsAppService
**Location**: `app/services/whatsapp_service.py`

**Purpose**: Handle WhatsApp Business API integration

**Key Methods**:
- `verify_webhook()`: Verify webhook subscription
- `process_webhook()`: Process incoming messages
- `send_message()`: Send text messages
- `upload_file()`: Upload images to OpenAI
- `_download_media()`: Download media from WhatsApp

**Features**:
- Message deduplication (MessageCache)
- Timestamp validation
- Image processing with OpenAI Vision
- Customer management integration

### ActionService
**Location**: `app/services/action_service.py`

**Purpose**: Manage custom functions/actions for OpenAI assistants

**Key Methods**:
- `register_action()`: Register new action
- `get_action()`: Retrieve action by name
- `list_actions()`: List all actions
- `execute_action()`: Execute action (local or remote)
- `convert_to_openai_tools()`: Convert actions to OpenAI tool format

**Storage**: Actions persisted in `app/data/actions.json`

### AuthService
**Location**: `app/services/auth_service.py`

**Purpose**: User authentication and authorization

**Key Methods**:
- `create_user()`: Register new user
- `authenticate_user()`: Login and generate JWT
- `get_user_by_email()`: Find user by email

**Security**: Uses bcrypt for password hashing, JWT for tokens

### ContactService
**Location**: `app/services/contact_service.py`

**Purpose**: Manage contacts in MariaDB

**Key Methods**:
- CRUD operations for contacts
- `set_chat_status()`: Update chat status
- `update_thread_id()`: Update conversation thread ID

---

## Database & Storage

### MariaDB
**Purpose**: Primary database for users, contacts, messages, labels

**Connection**: `app/database/mysql.py` - Uses `aiomysql` with connection pooling

**Tables**:
- `users`: User accounts
- `contacts`: Customer contacts
- `messages`: Message history
- `labels`: Contact labels

### Google Sheets
**Purpose**: Customer tracking and conversation management

**Integration**: `app/utils/google_sheets.py`

**Operations**:
- `check_customer_exists()`: Find customer by phone
- `insert_customer()`: Create new customer
- `update_customer_name()`: Update customer info
- `update_thread_id()`: Update conversation thread
- `set_chat_status()`: Set Live Chat status

**Service Account**: Uses Google Service Account credentials from `config/credentials/`

---

## Authentication

### JWT Token Authentication
- **Algorithm**: HS256
- **Token Expiry**: Configurable (default 24 hours)
- **Storage**: Tokens sent in Authorization header

### Flow:
```
1. User registers/logs in via POST /api/auth/register or /login
2. AuthService validates credentials
3. JWT token generated with user info
4. Token returned to client
5. Client includes token in Authorization header for protected routes
```

### Protected Routes
Currently, most routes are public. Authentication can be added using:
```python
from fastapi import Depends
from ..utils.auth_utils import get_current_user

@router.get("/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user": user}
```

---

## Deployment

### Docker Deployment

#### Prerequisites
1. Docker and Docker Compose installed
2. `.env` file with required variables

#### Required Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=your_openai_api_key
WHATSAPP_ASSISTANT_ID=your_assistant_id

# WhatsApp Business API
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_ACCESS_TOKEN=your_access_token
WHATSAPP_VERIFY_TOKEN=your_verify_token

# Database
MARIADB_HOST=host.docker.internal
MARIADB_USER=your_user
MARIADB_PASSWORD=your_password
MARIADB_DATABASE=your_database

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH=config/credentials/loyalty-service-account.json

# Application
HOST_URL=http://localhost
PORT=8085
PRODUCTION=false
```

#### Steps

1. **Create Docker network** (if using external network):
```bash
docker network create solutionesia_network
```

2. **Build and run**:
```bash
docker-compose up --build
```

3. **Access application**:
- API: `http://localhost:8085`
- API Docs: `http://localhost:8085/docs`

### Manual Deployment

1. **Install Conda**:
```bash
conda env create -f environment.yml
conda activate docgen
```

2. **Set environment variables**:
```bash
export OPENAI_API_KEY=your_key
# ... other variables
```

3. **Run application**:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8085 --reload
```

---

## Logging

### Application Logging
**Location**: `app/utils/app_logger.py`

**Log Files**:
- `app/logs/app/app.log`: Application logs
- `app/logs/app/requests.log`: HTTP request logs
- `app/logs/whatsapp/{phone_number}.log`: Per-customer WhatsApp logs

### Log Levels
- **INFO**: Normal operations
- **WARNING**: Non-critical issues
- **ERROR**: Errors requiring attention
- **DEBUG**: Detailed debugging information

### WhatsApp Message Logging
Each WhatsApp message is logged with:
- Message ID
- Timestamp
- Contact name
- Message type (text/image/status)
- Direction (incoming/outgoing/system)
- Message content

---

## Error Handling

### Exception Handling Strategy
1. **Service Layer**: Catches and logs errors, returns error responses
2. **Router Layer**: Catches service errors, converts to HTTP exceptions
3. **Middleware**: Logs all requests/responses

### Common Error Scenarios
- **Invalid API Key**: Returns 401/403
- **Missing Environment Variables**: Raises ValueError on startup
- **Database Connection Failure**: Logs error, continues with fallback
- **OpenAI API Errors**: Returns error response with details
- **WhatsApp Webhook Errors**: Returns success to prevent retries, logs error

---

## Testing

### Performance Tests
**Location**: `tests/`

- `test_concurrent_performance.py`: Tests concurrent thread creation
- `test_thread_performance.py`: Tests thread operations

### Running Tests
```bash
python -m pytest tests/
```

---

## Future Enhancements

1. **Authentication**: Add JWT protection to all routes
2. **Rate Limiting**: Implement rate limiting for API endpoints
3. **Caching**: Add Redis caching for frequently accessed data
4. **Monitoring**: Add Prometheus metrics and health checks
5. **WebSocket**: Real-time updates for chat conversations
6. **Multi-language**: Support for multiple languages in responses

---

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**
   - Check API key is valid
   - Verify assistant ID exists
   - Check rate limits

2. **WhatsApp Webhook Not Working**
   - Verify webhook URL is accessible
   - Check verify token matches
   - Ensure HTTPS is enabled (production)

3. **Database Connection Issues**
   - Verify MariaDB is running
   - Check connection credentials
   - Verify network connectivity

4. **Google Sheets Errors**
   - Verify service account credentials
   - Check sheet permissions
   - Ensure sheet exists and is accessible

---

## Contributing

1. Follow PEP 8 style guidelines
2. Add type hints to all functions
3. Write docstrings for public methods
4. Add tests for new features
5. Update documentation

---

## License

[Add your license information here]

---

## Support

For issues and questions, please open an issue on the repository.

