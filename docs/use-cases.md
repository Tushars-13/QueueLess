# QueueLess — Use Cases

**Project:** QueueLess
**Document Version:** 1.0
**Status:** Draft
**Related Document:** SRS v1.0

---

## 1. Purpose

This document defines the primary interactions between QueueLess users and the system.

The two primary actors in the MVP are:

1. Customer
2. Business Owner

The purpose of this document is to describe the expected user flows and system behavior for the core QueueLess features.

---

# 2. Actors

## 2.1 Customer

A customer uses QueueLess to discover businesses, view available services and staff, join a virtual queue, track their position, and receive information about when they should arrive.

## 2.2 Business Owner

A business owner uses QueueLess to create and manage a business profile, configure services and staff, operate daily queues, serve customers, and view basic analytics.

## 2.3 Staff

**No independent Staff actor exists in the MVP.**

Staff members are managed by the Business Owner and do not have separate accounts or permissions.

---

# 3. Customer Use Cases

## UC-01 — Register as Customer

**Actor:** Customer

**Goal:** Create a QueueLess customer account.

### Main Flow

```text
1. Customer opens QueueLess.
2. Customer selects "Join as Customer".
3. System displays registration form.
4. Customer enters required information.
5. Customer submits registration.
6. System validates the information.
7. System creates the customer account.
8. Customer is logged in.
9. Customer is redirected to the customer home page.
```

### Alternative Flow

If registration information is invalid:

```text
System → displays validation error
Customer → corrects information
Customer → submits again
```

---

# UC-02 — Login as Customer

**Actor:** Customer

**Goal:** Access an existing customer account.

### Main Flow

```text
1. Customer opens QueueLess.
2. Customer selects "Join as Customer".
3. Customer selects "Login".
4. Customer enters credentials.
5. System validates credentials.
6. System authenticates the customer.
7. Customer is redirected to the customer home page.
```

---

# UC-03 — Search for Business

**Actor:** Customer

**Goal:** Find a business where the customer wants to receive a service.

### Main Flow

```text
1. Customer opens the customer home page.
2. Customer enters a business name, category, service, or location.
3. System searches available businesses.
4. System displays matching businesses.
5. Customer selects a business.
6. System opens the business profile.
```

### Example

```text
Customer searches:

"Kallu Salon Yashoda Nagar"

             ↓

QueueLess displays:

Kallu Salon
Open
~15 min estimated wait
2 staff available
```

---

# UC-04 — Discover Nearby Businesses

**Actor:** Customer

**Goal:** Find businesses near the customer's location.

### Main Flow

```text
1. Customer opens the customer home page.
2. Customer selects a category or nearby option.
3. System obtains the required location information.
4. System finds relevant businesses.
5. System displays nearby businesses.
6. Customer selects a business.
```

### Example Categories

```text
Salon
Clinic
Repair Shop
Service Center
Barber
Other Local Services
```

---

# UC-05 — View Business Profile

**Actor:** Customer

**Goal:** Understand the business and its current queue situation before joining.

### Business Profile May Display

```text
Business Name
Business Photos
Location
Opening Hours
Business Status
Services
Pricing (if provided)
Staff
Staff Availability
Current Queue Information
Estimated Waiting Time
```

### Main Flow

```text
1. Customer selects a business.
2. System retrieves the business profile.
3. System displays business information.
4. Customer views available services and staff.
5. Customer chooses whether to join the queue.
```

---

# UC-06 — Select Service

**Actor:** Customer

**Goal:** Select the service the customer wants.

### Main Flow

```text
1. Customer opens a business profile.
2. Customer views available services.
3. Customer selects a service.
4. System records the selected service.
5. System displays relevant staff options if configured.
```

### Example

```text
Kallu Salon

Services:

Haircut       ₹150
Beard         ₹100
Hair Styling  ₹300
```

---

# UC-07 — Select Preferred Staff

**Actor:** Customer

**Goal:** Choose a specific service provider.

### Main Flow

```text
1. Customer selects a service.
2. System displays relevant staff members.
3. Customer views availability and queue information.
4. Customer selects a preferred staff member.
5. System associates the queue request with that staff member.
```

### Example

```text
Kallu       Available      3 waiting
Kanhaiya    Not Available
Raju        Available      1 waiting
Amit        Available      0 waiting
```

If Kanhaiya is unavailable, the customer cannot select Kanhaiya for a new queue request.

---

# UC-08 — Join General Queue

**Actor:** Customer

**Goal:** Receive service from any suitable available staff member.

### Main Flow

```text
1. Customer selects a service.
2. Customer chooses "Any Available Staff".
3. Customer submits the queue request.
4. System creates the request.
5. Business Owner accepts the request.
6. System assigns the customer to an appropriate queue/staff member.
7. System generates a daily token number.
8. Customer sees their queue information.
```

---

# UC-09 — Join Staff-Specific Queue

**Actor:** Customer

**Goal:** Receive service from a specific preferred staff member.

### Main Flow

```text
1. Customer selects a service.
2. Customer selects a preferred staff member.
3. Customer submits the queue request.
4. System creates the request.
5. Business Owner accepts the request.
6. Customer is added to the selected staff member's queue.
7. System generates a daily token number.
8. Customer receives queue information.
```

### Important Rule

The customer's **token number** and **queue position** are different.

Example:

```text
Token Number: #42
Queue Position: #1
```

---

# UC-10 — View Queue Position

**Actor:** Customer

**Goal:** Know the customer's current position in the selected queue.

### Example

```text
Token: #42

You're #1 in Kallu's queue.

2 customers are currently being served
or waiting in other queues.
```

The queue position changes as customers ahead of the user leave the queue or complete their service.

---

# UC-11 — View Estimated Waiting Time

**Actor:** Customer

**Goal:** Know approximately how long the customer needs to wait.

### Example

```text
You're #3 in queue.

Estimated wait:
~30 minutes

Recommended arrival:
10:25 AM
```

The ETA is an estimate and may change as queue conditions change.

---

# UC-12 — Cancel Queue Entry

**Actor:** Customer

**Goal:** Leave the queue when the customer no longer wants the service.

### Main Flow

```text
1. Customer opens active queue information.
2. Customer selects "Leave Queue".
3. System asks for confirmation.
4. Customer confirms.
5. System marks the queue entry as CANCELLED.
6. Queue position of remaining customers is updated.
```

---

# UC-13 — Receive Queue Notification

**Actor:** Customer

**Goal:** Receive an alert when the customer's turn is approaching.

### Possible Notifications

```text
"Your turn is approaching."

"You're #2 in queue."

"Please reach the salon in approximately 10 minutes."

"It's your turn. Please proceed to the service area."
```

---

# 4. Business Owner Use Cases

## UC-14 — Register as Business Owner

**Actor:** Business Owner

**Goal:** Create a business account.

### Main Flow

```text
1. Owner opens QueueLess.
2. Owner selects "Join as Business Owner".
3. Owner selects "Register".
4. Owner enters account information.
5. Owner enters business information.
6. Owner uploads optional business photos.
7. Owner configures location and opening hours.
8. System creates the business profile.
9. Owner is redirected to the business dashboard.
```

---

# UC-15 — Configure Business Profile

**Actor:** Business Owner

The owner can manage:

```text
Business Name
Business Category
Photos
Location
Opening Hours
Services
Pricing
Staff
```

Services, pricing, and staff are optional.

---

# UC-16 — Add Service

**Actor:** Business Owner

**Goal:** Add a service offered by the business.

### Example

```text
Service: Haircut
Price: ₹150
Estimated Service Time: 20 minutes
```

Pricing may be omitted.

---

# UC-17 — Add Staff

**Actor:** Business Owner

**Goal:** Add service providers to the business.

### Example

```text
Staff

Kallu
Kanhaiya
Raju
Amit
```

Staff accounts are not created in the MVP.

---

# UC-18 — Manage Staff Availability

**Actor:** Business Owner

**Goal:** Control which staff members can receive new customers.

### Example

```text
Kallu       Available
Kanhaiya    Not Available
Raju        Available
Amit        Available
```

If Kanhaiya is marked unavailable:

```text
Business Owner
      ↓
Kanhaiya → Not Available
      ↓
Customer UI
      ↓
Kanhaiya → Not Available
```

New customers cannot select Kanhaiya.

---

# UC-19 — Open Daily Queue

**Actor:** Business Owner

**Goal:** Start accepting customers for the current business day.

### Main Flow

```text
1. Owner logs into dashboard.
2. Owner selects today's queue.
3. Owner selects "Open Queue".
4. System changes queue status to OPEN.
5. Customers can now submit queue requests.
```

---

# UC-20 — Accept Customer Request

**Actor:** Business Owner

**Goal:** Accept a customer's request to enter the queue.

### Main Flow

```text
1. Customer submits queue request.
2. Request appears in Business Owner dashboard.
3. Owner reviews request.
4. Owner accepts request.
5. System adds customer to the appropriate queue.
6. System generates the customer's daily token.
7. Customer receives confirmation.
```

### Alternative

Owner may reject the request:

```text
REQUESTED → REJECTED
```

---

# UC-21 — Manage Active Queue

**Actor:** Business Owner

The owner can view:

```text
Token
Customer
Selected Service
Selected Staff
Status
Queue Position
```

Example:

```text
#41   Rahul     Kallu      COMPLETED
#42   Amit      Kallu      IN_SERVICE
#43   Ravi      Kallu      WAITING
#44   Suresh    Raju       WAITING
#45   Neha      ANY        WAITING
```

---

# UC-22 — Serve Customer

**Actor:** Business Owner

**Goal:** Move the next eligible customer into service.

### Main Flow

```text
1. Owner identifies the next eligible customer.
2. Owner selects "Serve".
3. System changes the customer's status to IN_SERVICE.
4. Queue positions are recalculated.
5. Relevant customers receive updated information.
```

---

# UC-23 — Complete Customer Service

**Actor:** Business Owner

### Main Flow

```text
1. Customer is currently IN_SERVICE.
2. Service is completed.
3. Owner selects "Complete".
4. System changes status to COMPLETED.
5. Next eligible customer becomes available.
6. Queue positions are updated.
```

Example:

```text
Before:

#42 → IN_SERVICE
#43 → WAITING
#44 → WAITING

After:

#42 → COMPLETED
#43 → IN_SERVICE
#44 → WAITING
```

---

# UC-24 — Skip Customer

**Actor:** Business Owner

**Goal:** Skip a customer who is unavailable or cannot currently be served.

```text
WAITING
   ↓
SKIPPED
```

The system recalculates the remaining queue.

---

# UC-25 — Mark Customer as No-Show

**Actor:** Business Owner

**Goal:** Mark a customer as absent when the customer fails to arrive within the required conditions.

```text
WAITING
   ↓
NO_SHOW
```

The system updates the queue accordingly.

---

# UC-26 — Close Daily Queue

**Actor:** Business Owner

**Goal:** Stop accepting new customers for the current day.

```text
OPEN
 ↓
CLOSED
```

After closure:

* New customers cannot join.
* Existing historical data remains stored.
* Queue statistics remain available.

---

# 5. Analytics Use Case

## UC-27 — View Business Analytics

**Actor:** Business Owner

**Goal:** Understand customer volume and queue performance.

### Dashboard may display:

```text
Today's Customers
Customers Served
Cancelled Customers
Skipped Customers
No-Shows
```

Historical:

```text
Monday      51
Tuesday     43
Wednesday   38
Thursday    61
Friday      72
Saturday    95
Sunday      27
```

The system may also display customer volume by time period.

Example:

```text
9 AM – 12 PM     High
12 PM – 4 PM     Low
5 PM – 9 PM      High
```

This helps the business owner understand customer traffic and potential peak hours.

---

# 6. Core Queue State Flow

The complete customer queue lifecycle:

```text
                 ┌─────────────┐
                 │  REQUESTED  │
                 └──────┬──────┘
                        │
                Owner Accepts
                        │
                        ▼
                 ┌─────────────┐
                 │   WAITING   │
                 └──────┬──────┘
                        │
                   Customer Called
                        │
                        ▼
                 ┌─────────────┐
                 │  IN_SERVICE │
                 └──────┬──────┘
                        │
                    Service Done
                        │
                        ▼
                 ┌─────────────┐
                 │  COMPLETED  │
                 └─────────────┘
```

Alternative paths:

```text
REQUESTED → REJECTED

WAITING → CANCELLED

WAITING → SKIPPED

WAITING → NO_SHOW
```

---

# 7. Token vs Queue Position

This is a critical QueueLess concept.

### Token Number

Represents the customer's sequential number for the business day.

```text
#41
#42
#43
#44
```

### Queue Position

Represents the customer's **current position in their specific active queue**.

Example:

```text
Customer: Amit

Daily Token: #42
Selected Staff: Kallu
Current Queue Position: #1
```

Therefore:

> **Token #42 does NOT mean that 41 customers are ahead of the customer.**

The customer-facing UI should clearly distinguish these two values.

---

# 8. Complete Example — Salon

Suppose Kallu Salon has:

```text
Kallu       Available
Kanhaiya    Available
Raju        Available
Amit        Not Available
```

Customer Rahul wants Kallu specifically.

He selects:

```text
Business:
Kallu Salon

Service:
Haircut

Staff:
Kallu
```

He joins the queue.

System assigns:

```text
Daily Token: #42
Queue Position: #1
Estimated Wait: ~15 min
```

Another customer joins Kallu's queue:

```text
Daily Token: #43
Queue Position: #2
```

When Rahul's service starts:

```text
#42 → COMPLETED
#43 → IN_SERVICE
```

The second customer's screen automatically changes:

```text
You are now #1.

Estimated wait: ~15 min
```

This demonstrates the fundamental purpose of QueueLess:

> **Customers maintain their place in the virtual queue without having to physically stand at the business.**

---

# 9. MVP Use Case Summary

| ID    | Use Case            | Actor    | MVP |
| ----- | ------------------- | -------- | --- |
| UC-01 | Register Customer   | Customer | ✅   |
| UC-02 | Customer Login      | Customer | ✅   |
| UC-03 | Search Business     | Customer | ✅   |
| UC-04 | Nearby Businesses   | Customer | ✅   |
| UC-05 | View Business       | Customer | ✅   |
| UC-06 | Select Service      | Customer | ✅   |
| UC-07 | Select Staff        | Customer | ✅   |
| UC-08 | Join General Queue  | Customer | ✅   |
| UC-09 | Join Staff Queue    | Customer | ✅   |
| UC-10 | View Queue Position | Customer | ✅   |
| UC-11 | View ETA            | Customer | ✅   |
| UC-12 | Leave Queue         | Customer | ✅   |
| UC-13 | Notifications       | Customer | ✅   |
| UC-14 | Register Business   | Owner    | ✅   |
| UC-15 | Configure Business  | Owner    | ✅   |
| UC-16 | Add Service         | Owner    | ✅   |
| UC-17 | Add Staff           | Owner    | ✅   |
| UC-18 | Staff Availability  | Owner    | ✅   |
| UC-19 | Open Queue          | Owner    | ✅   |
| UC-20 | Accept Request      | Owner    | ✅   |
| UC-21 | Manage Queue        | Owner    | ✅   |
| UC-22 | Serve Customer      | Owner    | ✅   |
| UC-23 | Complete Service    | Owner    | ✅   |
| UC-24 | Skip Customer       | Owner    | ✅   |
| UC-25 | No-Show             | Owner    | ✅   |
| UC-26 | Close Queue         | Owner    | ✅   |
| UC-27 | View Analytics      | Owner    | ✅   |

---
