# QueueLess — SRS v1.0

**Software Requirements Specification**

> **Project:** QueueLess
> **Document Version:** 1.0
> **Status:** Draft
> **Target:** MVP
> **Primary Platform:** Responsive Web Application

---

## 1. Introduction

### 1.1 Project Overview

**QueueLess** is a digital queue-management SaaS platform designed to reduce the amount of physical waiting customers experience at local service businesses.

The platform allows businesses to create and manage their daily queues while allowing customers to discover businesses, select services and optionally preferred service providers, join virtual queues, monitor their queue position, receive estimated waiting times, and arrive when their turn is approaching.

The initial version of QueueLess will be developed as a **responsive web application** rather than a native mobile application. This allows customers and business owners to access the platform directly through a web browser without installing an application.

---

## 1.2 Problem Statement

Customers visiting local service businesses often have to physically wait in queues for an uncertain amount of time.

Examples include:

* Salons and barbershops
* Clinics
* Repair shops
* Local service centers
* Other businesses where customers are served sequentially

The existing process creates several problems:

1. Customers must physically remain at the business while waiting.
2. Customers often don't know how long they will have to wait.
3. Customers may waste significant amounts of time during low-value waiting periods.
4. Businesses have limited visibility into their queue performance.
5. Customers who temporarily leave the physical queue may lose their position.
6. Customers may prefer a particular staff member, making the queue-management process more complicated.
7. Businesses may not have historical information about customer volume and peak hours.

---

# 2. Proposed Solution

QueueLess introduces a **virtual queue system** that separates *waiting in line* from *physically waiting at the business*.

Instead of physically standing in a queue, a customer can:

```text
Discover Business
       ↓
View Services & Availability
       ↓
Select Service
       ↓
Select Preferred Staff
       ↓
Join Virtual Queue
       ↓
Receive Token
       ↓
Track Queue Position
       ↓
Monitor Estimated Wait
       ↓
Receive Notification
       ↓
Arrive When Turn Is Near
       ↓
Receive Service
```

The business owner can manage the queue digitally and track customer flow throughout the day.

---

# 3. Goals and Objectives

### 3.1 Primary Goals

QueueLess aims to:

* Reduce unnecessary physical waiting.
* Provide customers with visibility into their queue position.
* Provide estimated waiting times.
* Preserve fair queue ordering.
* Allow customers to choose a preferred service provider when available.
* Allow customers to join a general queue when they have no staff preference.
* Give businesses a simple digital queue-management system.
* Provide businesses with basic historical queue analytics.

### 3.2 Product Principle

> **The system should hide technical complexity from users and make joining and managing a queue as simple as making a digital payment.**

The backend may involve complex technologies such as real-time communication, database transactions, and queue-management logic, but the customer experience should remain simple.

---

# 4. System Users

QueueLess will initially have two primary user types.

## 4.1 Customer

A customer uses QueueLess to:

* Discover nearby businesses.
* Search for businesses.
* View business information.
* View services and optional pricing.
* View staff availability.
* Select a preferred staff member.
* Join a specific staff queue.
* Join a general queue.
* Receive a token number.
* View current queue position.
* View estimated waiting time.
* Receive notifications.
* Cancel/leave the queue.
* View queue status.

---

## 4.2 Business Owner

A business owner uses QueueLess to:

* Create and manage a business profile.
* Upload business photos.
* Add business location.
* Configure opening hours.
* Add services.
* Add optional pricing.
* Add staff/service providers.
* Mark staff as available/unavailable.
* Open the daily queue.
* Accept/reject customer requests.
* View active queues.
* Serve customers.
* Mark customers as completed.
* Skip customers when necessary.
* Close the daily queue.
* View basic business analytics.

---

# 5. Staff Role

### MVP Decision

**Staff will not have independent user accounts in the MVP.**

Staff members will be managed by the business owner.

For example:

```text
Business: Kallu Salon

Staff:
├── Kallu       Available
├── Kanhaiya    Not Available
├── Raju        Available
└── Amit        Available
```

A future version may introduce individual staff accounts and permissions.

---

# 6. Functional Requirements

Ab ye important section hai. Yahan hum actual system behavior define kar rahe hain.

## 6.1 Authentication

**FR-01:** The system shall allow users to register as a Customer or Business Owner.

**FR-02:** The system shall allow registered users to log in.

**FR-03:** The system shall provide role-specific interfaces based on whether the user is a Customer or Business Owner.

---

## 6.2 Business Profile

**FR-04:** The system shall allow a Business Owner to create a business profile.

**FR-05:** The system shall allow the Business Owner to provide the business name, category, location, and opening hours.

**FR-06:** The system shall allow the Business Owner to upload business photos.

**FR-07:** The system shall allow the Business Owner to add services.

**FR-08:** The system shall allow the Business Owner to optionally add prices for services.

**FR-09:** Services and pricing shall not be mandatory for creating a business.

---

## 6.3 Staff Management

**FR-10:** The system shall allow the Business Owner to add staff/service providers.

**FR-11:** Adding staff shall be optional.

**FR-12:** The Business Owner shall be able to mark an individual staff member as available or unavailable.

**FR-13:** Customers shall not be able to join a queue assigned to a staff member marked unavailable.

---

# 7. Queue Management

## 7.1 Daily Queue

**FR-14:** The system shall maintain a separate queue for each business operating day.

**FR-15:** A Business Owner shall be able to open the queue for the current business day.

**FR-16:** Customers shall only be able to join an active/open queue.

**FR-17:** The Business Owner shall be able to close the queue.

**FR-18:** Closed queues shall remain available for historical records and analytics but shall not accept new customers.

---

# 8. Customer Queue Joining

**FR-19:** Customers shall be able to search for businesses.

**FR-20:** Customers shall be able to discover nearby businesses.

**FR-21:** Customers shall be able to view a business profile before joining its queue.

**FR-22:** Customers shall be able to select a service, where services are configured by the business.

**FR-23:** Customers shall optionally select a preferred staff member.

**FR-24:** Customers shall be able to join a specific staff member's queue.

**FR-25:** Customers shall be able to join a general queue when they do not have a staff preference.

**FR-26:** The system shall create a queue entry for the customer after a successful queue request/acceptance flow.

---

# 9. Token Number vs Queue Position

**FR-27:** The system shall assign each customer a unique sequential **daily token number**.

For example:

```text
Token #41
Token #42
Token #43
Token #44
```

The token represents the customer's position in the **day's overall customer sequence**, not their current queue position.

**FR-28:** The system shall independently calculate the customer's current position within their selected queue.

For example:

```text
Token: #42
Queue Position: #1
```

**FR-29:** Queue position shall dynamically change as customers ahead of the customer are served, cancelled, skipped, or otherwise leave the queue.

This distinction is a **core QueueLess requirement**.

---

# 10. Queue Ordering & Fairness

**FR-30:** The system shall maintain a FIFO (First In, First Out) ordering for customers within a queue under normal circumstances.

**FR-31:** A customer shall not lose their queue position merely because they temporarily leave the physical premises, provided they remain an active queue member and arrive within the allowed conditions.

**FR-32:** Business Owners shall be able to explicitly skip, cancel, or mark a customer as a no-show when applicable.

---

# 11. Queue Status

A queue entry may transition through states such as:

```text
REQUESTED
    ↓
ACCEPTED
    ↓
WAITING
    ↓
CALLED
    ↓
IN_SERVICE
    ↓
COMPLETED
```

Alternative states:

```text
REQUESTED → REJECTED

WAITING → CANCELLED
WAITING → NO_SHOW
```

**FR-33:** The system shall maintain the current state of each queue entry.

**FR-34:** The Business Owner shall be able to move a customer through appropriate queue states.

**FR-35:** The system shall automatically update the positions of remaining customers when queue state changes occur.

---

# 12. ETA & Notifications

**FR-36:** The system shall calculate an estimated waiting time for customers.

For the initial implementation, the estimate may be based on:

> **Customers ahead × Estimated Average Service Time**

**FR-37:** The system shall display estimated waiting time to the customer.

**FR-38:** The system shall provide an estimated/recommended arrival time where sufficient information is available.

Example:

> **Estimated wait: 20 minutes**
> **Recommended arrival: 10:25 AM**

**FR-39:** The system shall notify customers when their turn is approaching.

**FR-40:** The system shall notify customers when their turn is reached.

ETA will be treated as an **estimate**, not a guaranteed service time.

---

# 13. Business Queue Operations

**FR-41:** The Business Owner shall be able to view the active queue.

**FR-42:** The Business Owner shall be able to identify customers using their daily token numbers.

Example:

```text
#41 → Completed
#42 → In Service
#43 → Waiting
#44 → Waiting
```

**FR-43:** The Business Owner shall be able to serve the next eligible customer.

**FR-44:** The Business Owner shall be able to mark a service as completed.

**FR-45:** The system shall automatically advance the appropriate waiting customer when the current service is completed.

---

# 14. Analytics

The MVP shall provide basic operational analytics.

**FR-46:** The system shall record the number of customers joining a business queue.

**FR-47:** The system shall record the number of customers served.

**FR-48:** The system shall record cancelled/skipped/no-show customers.

**FR-49:** The Business Owner shall be able to view customer counts by day.

**FR-50:** The system shall provide basic information about customer volume across different times of the day.

This can help businesses identify patterns such as:

```text
9 AM – 12 PM     High
12 PM – 4 PM     Low
5 PM – 9 PM      High
```

---

# 15. Non-Functional Requirements

Abhi isko concise rakhte hain.

### Performance

* Common user actions should respond quickly under normal load.
* Queue updates should be reflected near real-time.

### Reliability

* Concurrent queue operations must not corrupt queue state.
* The same customer must not accidentally be served twice.

### Security

* Business management functionality must require authentication.
* Customers must not be able to modify business queue state.
* Users must only access resources they are authorized to access.

### Scalability

* The architecture should support multiple businesses and independent queues.

### Usability

* Customer workflows should be simple and mobile-friendly.
* A customer should be able to join a queue with minimal steps.

### Maintainability

* Frontend, backend, queue logic, and data-access logic should remain modular.

### Privacy

* The MVP should avoid unnecessary collection of sensitive customer information.
* Live customer GPS tracking will not be required for the initial version.

---

# 16. MVP Scope

### Included

```text
✓ Customer authentication
✓ Business authentication
✓ Business profiles
✓ Photos
✓ Services
✓ Optional pricing
✓ Optional staff
✓ Staff availability
✓ Daily queues
✓ Search / nearby businesses
✓ Staff-specific queues
✓ General queue
✓ Token numbers
✓ Dynamic queue positions
✓ FIFO ordering
✓ Accept/reject flow
✓ Serve/complete/skip
✓ Basic ETA
✓ Notifications
✓ Basic analytics
✓ Responsive web UI
```

### Deferred

```text
○ Individual staff accounts
○ QR-based joining
○ SMS / WhatsApp notifications
○ Payments
○ Ratings & reviews
○ Multiple business branches
○ Subscription/billing
○ Live GPS tracking
○ Advanced ETA prediction
○ Machine-learning-based forecasting
○ Native Android/iOS applications
```

---

# 17. Core Business Rules

Ye section especially important hai because **requirements aur business rules same cheez nahi hote.**

### BR-01 — Daily Queue

Every business has a separate queue for each operating day.

### BR-02 — Token

Each accepted customer receives a unique daily token.

### BR-03 — Position

Token number and queue position are independent values.

### BR-04 — FIFO

Customers are normally served in the order in which they entered the relevant queue.

### BR-05 — Staff Availability

Unavailable staff cannot receive new queue assignments.

### BR-06 — Queue Closure

A closed queue cannot accept new customers.

### BR-07 — Historical Data

Previous queues remain stored for analytics but cannot accept new customers.

### BR-08 — ETA

ETA is an estimate and may change as queue conditions change.

---

## 18. High-Level User Journey

### Customer

```text
Google/Search
      ↓
QueueLess
      ↓
Join as Customer
      ↓
Register/Login
      ↓
Search / Nearby
      ↓
Business Profile
      ↓
Service
      ↓
Preferred Staff / Any Staff
      ↓
Join Queue
      ↓
Token + Position + ETA
      ↓
Notification
      ↓
Arrive
      ↓
Service
      ↓
Completed
```

### Business

```text
QueueLess
   ↓
Join as Business Owner
   ↓
Register/Login
   ↓
Create Business Profile
   ↓
Services / Pricing / Staff
   ↓
Open Today's Queue
   ↓
Accept Customers
   ↓
Manage Queue
   ↓
Serve → Complete
   ↓
View Analytics
   ↓
Close Queue
```

---

# 19. Initial Technology Direction

Technology decisions ko abhi **final implementation contract** nahi maanenge, but current planned stack:

| Layer               | Technology         |
| ------------------- | ------------------ |
| Frontend            | Next.js            |
| Language            | TypeScript         |
| Backend             | FastAPI            |
| Database            | PostgreSQL         |
| Real-time / Pub/Sub | Redis + WebSockets |
| API style           | REST               |
| Version Control     | Git + GitHub       |

Aur tumhare learning goal ko dekhte hue hum **ek-ek technology ko project ke requirement se connect karke seekhenge**, instead of pehle 2 hafte sirf tutorials dekhna.

---

## 20. Definition of MVP Success

QueueLess MVP successful maana jayega agar ek complete workflow reliably perform ho:

> **Business registers → creates profile → adds optional staff/services → opens today's queue → customer discovers business → selects service/staff → joins queue → receives token → tracks position/ETA → business manages queue → customer is served → historical data is recorded.**

**Ye hamara "golden path" hai.**

---
