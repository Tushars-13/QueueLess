# QueueLess — High-Level Design

**Project:** QueueLess
**Document Version:** 1.0
**Status:** Draft
**Related Documents:** SRS v1.0, Use Cases v1.0

---

# 1. Purpose

This document describes the high-level architecture and system design of QueueLess.

It defines the major system components, their responsibilities, communication patterns, data flow, and key architectural decisions required to implement the QueueLess MVP.

This document intentionally avoids detailed class-level implementation. Those details will be covered later in the Low-Level Design (LLD).

---

# 2. System Overview

QueueLess will be implemented as a **responsive web-based SaaS application**.

The system consists primarily of:

```text
Frontend
   ↓
Backend API
   ↓
Database
   +
Real-Time Infrastructure
```

### High-Level Architecture

```text
                         ┌──────────────────────┐
                         │       Users          │
                         │                      │
                         │ Customer / Business  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      Next.js         │
                         │   Web Application    │
                         └──────────┬───────────┘
                                    │
                         REST / WebSocket
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │     Backend API      │
                         └──────┬─────────┬─────┘
                                │         │
                         ┌──────┘         └──────┐
                         ▼                       ▼
                ┌─────────────────┐      ┌─────────────────┐
                │   PostgreSQL    │      │      Redis      │
                │                 │      │                 │
                │ Persistent Data │      │ Cache / PubSub  │
                └─────────────────┘      └─────────────────┘
```

---

# 3. Architectural Style

QueueLess will initially follow a **modular monolithic architecture**.

The backend will be deployed as one FastAPI application, but internally separated into logical modules.

```text
                    FastAPI Application
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
       ▼                   ▼                   ▼
    Auth Module       Business Module      Queue Module
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                    Data Access Layer
                           │
                           ▼
                      PostgreSQL
```

### Why Modular Monolith?

For the MVP, microservices would introduce unnecessary complexity.

We want:

* Simple development
* Easy local setup
* Easier debugging
* Fewer deployment problems
* Clear separation of responsibilities

If QueueLess grows significantly in the future, individual components can be extracted into services.

---

# 4. Major System Components

## 4.1 Frontend — Next.js

The frontend provides the user interface for both Customers and Business Owners.

### Responsibilities

* Authentication screens
* Customer interface
* Business dashboard
* Business discovery
* Search
* Business profiles
* Queue interface
* Queue position display
* ETA display
* Notifications
* Analytics dashboard

The frontend will be responsive and optimized primarily for mobile customers.

---

# 5. Backend — FastAPI

FastAPI will act as the main application backend.

### Responsibilities

* Authentication
* Authorization
* Business management
* Customer management
* Queue management
* Staff management
* Service management
* Queue state transitions
* Token generation
* Position calculation
* ETA calculation
* Analytics
* WebSocket connections
* API validation

The backend will contain the core business logic of QueueLess.

---

# 6. PostgreSQL

PostgreSQL will be the **primary source of truth** for persistent application data.

It will store:

```text
Users
Businesses
Services
Staff
Daily Queues
Queue Entries
Queue Events
Notifications
Analytics-related records
```

### Important Architectural Rule

> **PostgreSQL is authoritative for queue state.**

Redis will not be treated as the permanent source of truth for queue membership or queue ordering.

This ensures that queue operations can use database transactions and consistency mechanisms.

---

# 7. Redis

Redis will initially have two major responsibilities.

### 7.1 Real-Time Pub/Sub

When queue state changes:

```text
Customer joins
      ↓
FastAPI
      ↓
PostgreSQL
      ↓
Redis Pub/Sub
      ↓
Connected clients
```

This allows multiple connected users to receive queue updates.

### 7.2 Caching

Redis may be used for frequently accessed temporary information where appropriate.

Examples:

* Frequently requested business information
* Temporary session-related data
* Short-lived computed values

Caching decisions will be introduced only where necessary.

---

# 8. WebSockets

QueueLess requires near real-time updates.

Polling alone would mean customers repeatedly asking:

> "Has my position changed?"

Instead, WebSockets will allow the server to push important queue updates to connected clients.

### Example

Business Owner:

```text
#42 → COMPLETED
```

Backend:

```text
Queue state changed
       ↓
Redis Pub/Sub
       ↓
WebSocket
```

Customer:

```text
You're now #1 in queue.
```

---

# 9. REST API

REST APIs will be used for normal request-response operations.

Examples:

```text
POST /auth/register
POST /auth/login

GET  /businesses
GET  /businesses/{id}

POST /queues
GET  /queues/{id}

POST /queues/{id}/join
POST /queues/{id}/accept

POST /queue-entries/{id}/cancel
POST /queue-entries/{id}/serve
POST /queue-entries/{id}/complete
```

Exact API contracts will be defined later in the API Specification document.

---

# 10. Customer Architecture Flow

A typical customer journey:

```text
Customer
   │
   ▼
Next.js
   │
   │ Search
   ▼
FastAPI
   │
   ▼
PostgreSQL
   │
   ▼
Business Results
   │
   ▼
Customer selects business
   │
   ▼
View Business Profile
   │
   ▼
Select Service
   │
   ▼
Select Staff / Any Staff
   │
   ▼
Join Queue Request
   │
   ▼
FastAPI
   │
   ▼
Queue Engine
   │
   ▼
PostgreSQL
   │
   ▼
Token + Queue Position + ETA
```

---

# 11. Business Owner Architecture Flow

```text
Business Owner
       │
       ▼
   Next.js
       │
       ▼
   FastAPI
       │
       ├──────────────┐
       ▼              ▼
Business Module    Queue Module
       │              │
       └──────┬───────┘
              ▼
         PostgreSQL
```

The Business Owner can:

* Configure business
* Configure services
* Configure staff
* Change staff availability
* Open/close queue
* Accept/reject requests
* Serve customers
* Complete services
* Skip/no-show customers
* View analytics

---

# 12. Queue Engine

The **Queue Engine is the core domain component** of QueueLess.

Its responsibility is to maintain consistent queue behavior.

### Responsibilities

```text
Join Queue
Accept Request
Generate Token
Calculate Position
Serve Next
Skip
Cancel
No-Show
Complete
Close Queue
```

The queue engine must enforce business rules such as:

* FIFO ordering
* Valid state transitions
* Staff availability
* Queue status
* Token uniqueness
* Position recalculation

---

# 13. Token Architecture

Token numbers and queue positions are different concepts.

### Token

Persistent daily identifier:

```text
#41
#42
#43
#44
```

### Position

Dynamic position within the selected queue:

```text
Token #42
Position #1
```

The token number should remain unchanged throughout the queue entry's lifecycle.

The queue position is calculated dynamically based on the current state of the relevant queue.

---

# 14. Queue Partitioning

A business can have multiple logical queues based on staff/service configuration.

Example:

```text
Kallu Salon
│
├── Kallu Queue
│     ├── Token #42
│     ├── Token #47
│     └── Token #51
│
├── Raju Queue
│     ├── Token #43
│     └── Token #48
│
└── General Queue
      ├── Token #44
      └── Token #49
```

Customers selecting a specific staff member enter that staff member's queue.

Customers selecting **Any Available Staff** enter the general queue.

The exact assignment algorithm for the general queue will be defined during LLD.

---

# 15. Queue State Management

Queue entries follow controlled state transitions.

```text
                    ┌─────────────┐
                    │  REQUESTED  │
                    └──────┬──────┘
                           │
                      Accepted
                           │
                           ▼
                    ┌─────────────┐
                    │   WAITING   │
                    └──────┬──────┘
                           │
                         Called
                           │
                           ▼
                    ┌─────────────┐
                    │  IN_SERVICE │
                    └──────┬──────┘
                           │
                       Completed
                           │
                           ▼
                    ┌─────────────┐
                    │  COMPLETED  │
                    └─────────────┘
```

Alternative transitions:

```text
REQUESTED → REJECTED

WAITING → CANCELLED
WAITING → SKIPPED
WAITING → NO_SHOW
```

Invalid state transitions must be rejected by the backend.

---

# 16. Concurrency Handling

QueueLess must handle simultaneous actions safely.

### Example

Two business users attempt:

```text
Serve Next
```

at the same time.

Without proper concurrency handling:

```text
Staff A → Customer #42
Staff B → Customer #42
```

This would be incorrect.

The backend must guarantee:

```text
Customer #42 → served exactly once
```

This will be handled using database transactions and appropriate PostgreSQL concurrency mechanisms.

Detailed implementation will be defined in the LLD.

---

# 17. ETA Architecture

The initial ETA engine will use a simple estimation model.

Conceptually:

```text
Customers Ahead
       +
Estimated Service Duration
       ↓
Estimated Waiting Time
```

Example:

```text
Customers ahead = 3
Average service time = 15 min

Estimated Wait ≈ 45 min
```

The ETA should be recalculated when relevant queue events occur.

Examples:

```text
Customer joins
Customer cancels
Customer completed
Customer skipped
Staff becomes unavailable
Staff becomes available
```

ETA is an estimate, not a guaranteed service time.

---

# 18. Notification Architecture

Notifications will be triggered by important queue events.

Example:

```text
Queue Event
     │
     ▼
Notification Logic
     │
     ▼
Notification
     │
     ▼
Customer
```

Possible events:

```text
Queue request accepted
Position changed significantly
Turn approaching
Turn reached
Queue cancelled/closed
```

The initial implementation may use in-app notifications.

External channels such as SMS or WhatsApp are deferred.

---

# 19. Analytics Architecture

Queue activity will generate historical records.

Conceptually:

```text
Queue Events
     │
     ▼
Persistent Records
     │
     ▼
Analytics Queries
     │
     ▼
Business Dashboard
```

The system can derive:

* Total customers
* Customers served
* Cancellations
* No-shows
* Daily customer volume
* Time-based customer volume

Example:

```text
Monday
Customers: 51

Tuesday
Customers: 43

Wednesday
Customers: 38
```

---

# 20. Daily Queue Architecture

Each business has a separate queue for each operating day.

Conceptually:

```text
Business
   │
   ├── Queue — 2026-09-06
   │
   ├── Queue — 2026-09-07
   │
   └── Queue — 2026-09-08
```

The current day's queue can be:

```text
OPEN
CLOSED
```

Historical queues remain stored for analytics.

---

# 21. Data Flow — Customer Joins Queue

```text
Customer
   │
   ▼
Next.js
   │
   │ POST Join Queue
   ▼
FastAPI
   │
   ├── Validate customer
   ├── Validate business
   ├── Validate queue
   ├── Validate staff
   └── Create queue entry
            │
            ▼
        PostgreSQL
            │
            ▼
      Queue Event
            │
            ▼
       Redis Pub/Sub
            │
            ▼
     WebSocket Clients
```

---

# 22. Data Flow — Customer Completed

```text
Business Owner
      │
      ▼
Next.js Dashboard
      │
      │ Complete Customer
      ▼
FastAPI
      │
      ▼
Queue Engine
      │
      ├── Validate state
      ├── Mark customer COMPLETED
      ├── Identify next customer
      ├── Recalculate positions
      └── Recalculate ETA
              │
              ▼
         PostgreSQL
              │
              ▼
         Redis Pub/Sub
              │
              ▼
       Connected Customers
```

---

# 23. Security Architecture

Authentication will be required for protected operations.

```text
User
 │
 ▼
Login
 │
 ▼
Authentication
 │
 ▼
Authenticated Session
 │
 ▼
Authorized API Requests
```

Authorization rules will ensure:

* Customers cannot modify business settings.
* Customers cannot serve/complete other customers.
* Business Owners can only manage their own business.
* Business Owners cannot manage another business's queue.

Detailed authentication implementation will be covered later.

---

# 24. Error Handling

The backend will return appropriate errors for invalid operations.

Examples:

```text
Queue is closed
Staff is unavailable
Customer already in queue
Invalid queue state
Business not found
Unauthorized operation
Invalid credentials
```

The frontend should convert technical errors into simple user-friendly messages.

Example:

Instead of:

```text
HTTP 409 Conflict
```

the customer should see:

> **You are already in this queue.**

---

# 25. Deployment Architecture — Initial

For development:

```text
┌──────────────┐
│   Next.js    │
│   Frontend   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   FastAPI    │
│   Backend    │
└──┬────────┬──┘
   │        │
   ▼        ▼
PostgreSQL Redis
```

Initially, the entire system should be runnable locally.

Production deployment can be designed after the MVP is working.

---

# 26. Technology Responsibilities

| Technology | Responsibility              |
| ---------- | --------------------------- |
| Next.js    | Web UI                      |
| TypeScript | Frontend type safety        |
| FastAPI    | Backend/API                 |
| PostgreSQL | Persistent data             |
| Redis      | Pub/Sub + selective caching |
| WebSockets | Real-time updates           |
| Git        | Version control             |
| GitHub     | Source code + documentation |

---

# 27. Architectural Principles

QueueLess will follow these principles:

### 1. PostgreSQL as Source of Truth

Persistent queue state must be stored in PostgreSQL.

### 2. Backend Owns Business Logic

Queue rules must not be implemented only in the frontend.

### 3. Simple User Experience

Technical complexity should remain hidden from customers and business owners.

### 4. Modular Architecture

The backend should have clear domain modules.

### 5. Real-Time Where Necessary

Queue state changes should propagate to connected clients with minimal delay.

### 6. MVP First

Architecture should solve the MVP without introducing unnecessary infrastructure.

### 7. Extensibility

The design should allow future additions such as staff accounts, payments, multiple branches, and advanced ETA prediction.

---

# 28. Future Architectural Evolution

The MVP will start as a modular monolith:

```text
             FastAPI
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
    Auth     Business    Queue
      │         │         │
      └─────────┼─────────┘
                ▼
           PostgreSQL
```

If the product grows, components can later be separated:

```text
                    API Gateway
                         │
       ┌─────────────────┼─────────────────┐
       ▼                 ▼                 ▼
   Auth Service     Queue Service    Notification Service
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                    Event System
```

This is **not part of the MVP implementation**.

---

# 29. HLD Summary

The QueueLess MVP will use a modular monolithic architecture consisting of:

```text
Customer / Business Owner
            │
            ▼
       Next.js Web App
            │
       REST + WebSocket
            │
            ▼
       FastAPI Backend
            │
       ┌────┴────┐
       ▼         ▼
 PostgreSQL    Redis
```

The most important component is the **Queue Engine**, which maintains queue consistency, FIFO ordering, token generation, position calculation, state transitions, and ETA updates.

PostgreSQL will remain the authoritative source of persistent state, while Redis will primarily support real-time event distribution and selective caching.

---


### Documentation progress

| Document          | Status       |
| ----------------- | ------------ |
| SRS               | ✅ v1.0 Draft |
| Use Cases         | ✅ v1.0 Draft |
| **HLD**           | ✅ v1.0 Draft |
| Database Design   | ⏳ Next       |
| LLD               | ⏳ Later      |
| API Specification | ⏳ Later      |
| Testing Strategy  | ⏳ Later      |
| Deployment        | ⏳ Later      |

**Next `database-design.md` hoga**, aur woh particularly important hai because ab hum HLD ke components ko actual tables/entities mein translate karenge—especially **User → Business → Staff → Service → Daily Queue → Queue Entry → Queue Events** relationship.
