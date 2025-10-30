# EDS ASSISTANT - PROJECT CONSTITUTION

**Project Type:** AI/ML Healthcare Assistant for EDS (Ehlers-Danlos Syndrome)  
**Scope:** Resume-level demonstration project  
**Philosophy:** Simplicity over complexity, functionality over perfection

---

## CORE PRINCIPLES

1. **Backend-First Development** - All current efforts focus on backend and database architecture
2. **API-Driven Design** - Frontend communication via RESTful APIs for future JS framework integration
3. **Modular Architecture** - Leverage pre-built components for specialized tasks (file extraction, RAG, fine-tuned models)
4. **Context Efficiency** - Lazy-load skills from Skills folder.

---

## PROJECT FEATURES

### 1. Symptom Analysis & Information Retrieval

- Process user-provided symptoms
- Provide EDS-related medical information
- Utilize RAG (Retrieval-Augmented Generation) for accurate responses

### 2. Medical Document Processing

- Accept lab reports in multiple formats (images, PDFs)
- Extract and analyze relevant medical data
- Store processed information securely

### 3. Multi-Modal Input

- Text-based queries
- Speech-to-text input capability
- Natural language processing for medical context

### 4. Intelligent Memory Management

- RAG services for information retrieval
- Long-term conversation memory
- Context-aware responses based on user history

### 5. User Authentication & Management

- Secure user registration and login
- Session management
- User-specific data isolation

### 6. Conversational Interface

- ChatGPT-like interaction model
- Persistent chat history
- Thread-based conversations

---

## TECHNICAL STACK

- **Framework:** Django (Python)
- **Database:** PostgreSQL
- **Authentication:** Django built-in auth system
- **API:** Django REST Framework
- **Testing Interface:** Vanilla HTML (basic, lightweight)

---

## DEVELOPMENT WORKFLOW

### Pre-Built Components (Already Handled)

- Data extraction from medical files
- Fine-tuned ML model
- RAG service implementation
- Related utility modules

### Current Development Focus

1. Database schema and models
2. Authentication system
3. API endpoints (not with forntend) (only model APIs)
4. Chat functionality and persistence
5. Integration points for pre-built components
6. Basic test frontend

### Future Development (Out of Scope)

- Production frontend with JS framework
- Advanced UI/UX
- Deployment optimization

---

## ARCHITECTURAL GUIDELINES

### Database Design

- User profiles and authentication
- Chat sessions and message history
- Document storage metadata
- RAG vector embeddings storage
- User-specific medical data

### API Structure

- RESTful endpoints
- Clear request/response schemas
- Proper HTTP status codes
- Token-based authentication

### Integration Points

- File processing service hooks
- RAG service endpoints
- ML model inference endpoints
- Speech-to-text service integration

---

## SKILL-BASED DEVELOPMENT PROTOCOL

**Location:** `Skills/` folder contains task-specific instructions

**Process:**

1. Identify required functionality
2. Load relevant skill file from Skills folder
3. Implement based on skill instructions
4. Clear skill from context after completion
5. Move to next functionality

**Purpose:** Maintain clean context window and focused development

---

## CRITICAL REMINDERS

- ⚠️ **ALWAYS** refer to this constitution periodically during development
- ⚠️ Pre-built components (file extraction, RAG, fine-tuned model) will be provided - DO NOT recreate
- ⚠️ Keep backend simple and functional - this is a demonstration project
- ⚠️ Test frontend is for API validation only - minimal styling/features
- ⚠️ PostgreSQL is mandatory for database
- ⚠️ Follow Django best practices but avoid over-engineering

---

## PROJECT BOUNDARIES

### In Scope

✓ Django backend architecture  
✓ PostgreSQL database  
✓ REST APIs  
✓ User authentication  
✓ Chat persistence  
✓ Integration scaffolding for pre-built services  
✓ Basic HTML test interface

### Out of Scope

✗ Production frontend  
✗ Advanced deployment configurations  
✗ Recreating pre-built ML/RAG components  
✗ Mobile applications 

---

## SUCCESS CRITERIA

A successful implementation will:

- Authenticate users securely
- Accept and store chat messages
- Integrate with provided ML/RAG services
- Process uploaded medical documents
- Provide conversational AI responses
- Maintain conversation history
- Expose clean, documented APIs
- Include functional test interface

---

**Last Updated:** Project Initialization  
**Status:** Constitution Active  
**Next Step:** Begin with Skills-based implementation following this constitution
