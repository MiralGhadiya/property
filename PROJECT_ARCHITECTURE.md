# Desktop Valuation Platform - Complete Architecture & Workflow Documentation

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [System Architecture](#system-architecture)
4. [Core Components](#core-components)
5. [Database Models & Schema](#database-models--schema)
6. [Authentication & Authorization](#authentication--authorization)
7. [Key Workflows](#key-workflows)
8. [Async Task Processing](#async-task-processing)
9. [API Endpoints Structure](#api-endpoints-structure)
10. [Admin Features](#admin-features)
11. [Payment Integration](#payment-integration)
12. [Internationalization & Localization](#internationalization--localization)
13. [Logging & Monitoring](#logging--monitoring)
14. [Deployment & Setup](#deployment--setup)

---

## Project Overview

**Desktop Valuation** is a comprehensive FastAPI-based platform that provides automated property valuation services with subscription management, payment processing, and administrative capabilities. The platform serves users across multiple countries with localized pricing, currency conversion, and property-specific valuations using AI/LLM integration.

### Key Features

- **User Authentication**: Email-based registration with verification and password management
- **Property Valuations**: AI-powered property valuation generation with detailed PDF reports
- **Subscription Management**: Multi-tier subscription plans with country-specific pricing
- **Payment Processing**: Razorpay integration for secure payment handling
- **Admin Dashboard**: Comprehensive admin panel for user, subscription, and valuation management
- **Async Processing**: Celery-based background task processing for valuations and notifications
- **Multi-Country Support**: Automatic IP-based country detection, localized pricing, and currency conversion
- **User Feedback System**: Feedback collection and management interface
- **Email Notifications**: Automated email communications for registration, password reset, and subscription updates

---

## Technology Stack

### Backend Framework
- **FastAPI** (v0.124.4): Modern async Python web framework
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migration management

### Database & Caching
- **PostgreSQL**: Primary relational database (inferred from SQLAlchemy dialect)
- **Redis**: Message broker and result backend for Celery

### Async & Background Processing
- **Celery** (v5.6.0): Distributed task queue system
- **Celery Beat**: Scheduled task execution

### AI/LLM Integration
- **Google Generative AI**: Gemini integration for property analysis
- **OpenAI**: Alternative LLM provider for valuations

### Payment Processing
- **Razorpay**: Payment gateway integration

### Email & Communication
- **Jinja2** (v3.1.6): Email template rendering
- **email-validator**: Email validation

### Utilities & Helpers
- **phonenumbers** (v9.0.20): Phone number validation and formatting
- **bcrypt**: Password hashing and verification
- **passlib**: Password scheme management
- **pydantic**: Data validation and serialization
- **python-jose**: JWT token generation and verification
- **langsmith**: LLM monitoring and evaluation

### PDF Generation
- Custom PDF generator for valuation reports

---

## System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend/Clients                             │
│                    (Web, Mobile, Desktop)                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    HTTP/REST Requests
                             │
┌─────────────────────────────▼────────────────────────────────────────┐
│                        FastAPI Application                           │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Authentication Middleware                                    │   │
│  │ CORS Middleware                                              │   │
│  │ IP-Country Detection Middleware                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            Route Handlers & Services                         │   │
│  │  ├── Auth Routes (User & Admin)                             │   │
│  │  ├── Valuation Routes                                       │   │
│  │  ├── Subscription Routes                                    │   │
│  │  ├── Payment Routes                                         │   │
│  │  ├── User Feedback Routes                                   │   │
│  │  ├── Inquiry Routes                                         │   │
│  │  └── Admin Routes (Users, Dashboard, etc.)                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            Business Logic & Services                         │   │
│  │  ├── AuthService                                            │   │
│  │  ├── ValuationService                                       │   │
│  │  ├── SubscriptionService                                    │   │
│  │  ├── UserService                                            │   │
│  │  ├── CurrencyResolver & ExchangeRateService                │   │
│  │  ├── PricingService                                         │   │
│  │  └── LLM Integration (Gemini, OpenAI)                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼─────┐      ┌─────▼──────┐    ┌──────▼─────┐
    │PostgreSQL│      │Redis/Celery│    │ Email SMTP │
    │Database  │      │(Task Queue) │    │  Service   │
    └──────────┘      └─────┬──────┘    └────────────┘
                            │
                ┌───────────▼────────────┐
                │ Celery Worker Threads  │
                │ ├── Valuation Jobs     │
                │ ├── Subscription Tasks │
                │ ├── Currency Updates   │
                │ └── Email Notifications│
                └───────────────────────┘
```

### Module Structure

```
app/
├── __init__.py                 # Package initialization
├── main.py                     # FastAPI app configuration & setup
├── auth.py                     # Authentication utilities
├── common.py                   # Common utilities
├── deps.py                     # Dependency injection
├── schemas.py                  # Global Pydantic schemas
├── celery_app.py              # Celery configuration
├── database/
│   ├── db.py                  # Database connection & session
│   └── mixins.py              # SQLAlchemy mixins (UUID primary key)
├── models/                     # SQLAlchemy ORM models
│   ├── user.py                # User model
│   ├── valuation.py           # Valuation & ValuationJob models
│   ├── subscription.py        # Subscription & SubscriptionPlan models
│   ├── payment.py             # Payment tracking models
│   ├── feedback.py            # User feedback models
│   ├── inquiry.py             # Inquiry models
│   ├── auth.py                # Staff/Admin auth models
│   ├── country.py             # Country & pricing models
│   ├── exchange_rate.py       # Exchange rate data
│   ├── staff.py               # Staff member models
│   └── subscription_settings.py # Subscription configuration
├── routes/                     # API endpoint handlers
│   ├── auth.py                # User authentication endpoints
│   ├── valuation.py           # Valuation endpoints
│   ├── subscription.py        # Subscription endpoints
│   ├── payment.py             # Payment endpoints
│   ├── inquiry.py             # Inquiry endpoints
│   ├── user_feedback.py       # Feedback endpoints
│   └── admin/                 # Admin-specific endpoints
│       ├── auth.py            # Admin login/auth
│       ├── users.py           # User management
│       ├── subscription_plans.py
│       ├── user_subscriptions.py
│       ├── valuations.py      # Valuation management
│       ├── dashboard.py       # Admin dashboard metrics
│       ├── feedback.py        # Feedback management
│       ├── staff.py           # Staff management
│       ├── inquiries.py       # Inquiry management
│       └── country.py         # Country & pricing management
├── schemas/                    # Pydantic request/response schemas
│   ├── auth.py
│   ├── admin.py
│   ├── user.py
│   ├── valuation.py
│   ├── subscription.py
│   ├── feedback.py
│   ├── inquiry.py
│   ├── staff.py
│   └── token.py
├── services/                   # Business logic layer
│   ├── auth_service.py        # Authentication logic
│   ├── user_service.py        # User operations
│   ├── valuation_service.py   # Valuation processing
│   ├── subscription_service.py # Subscription management
│   ├── pricing.py             # Price calculation
│   ├── currency_resolver.py   # Currency conversion
│   ├── exchange_rate_service.py # Exchange rate management
│   ├── valuation_report_builder.py # Report generation logic
│   └── llm/
│       ├── gemini.py          # Google Gemini integration
│       └── openai.py          # OpenAI integration
├── tasks/                      # Celery background tasks
│   ├── valuation_tasks.py     # Async valuation processing
│   ├── subscription_tasks.py  # Subscription expiry & reminders
│   ├── expire_subscription_task.py # Subscription expiration
│   └── currency_tasks.py      # Exchange rate updates
├── middleware/                 # Custom middleware
│   ├── ip_country_middleware.py # IP-based country detection
│   └── ip_country.py          # IP geolocation utilities
├── utils/                      # Utility functions
│   ├── logger_config.py       # Logging setup
│   ├── email.py               # Email sending utilities
│   ├── pdf_generator.py       # PDF generation
│   ├── maps.py                # Map/location utilities
│   ├── phone.py               # Phone number utilities
│   ├── response.py            # Response formatting
│   └── date_filters.py        # Date utilities
├── templates/                  # HTML email templates
│   ├── index.html
│   ├── verify_email.html
│   ├── reset_password.html
│   └── valuation_template.html
├── scripts/                    # Development scripts
│   ├── create_superuser.py
│   └── add_country.py
└── logs/                       # Application logs
```

---

## Core Components

### 1. FastAPI Application (`app/main.py`)

The central setup file that:
- Initializes the FastAPI application
- Creates database tables (if not in production)
- Registers all middleware (CORS, IP-Country detection, ngrok headers)
- Includes all route blueprints
- Configures exception handlers

### 2. Database Layer (`app/database/`)

**db.py**: 
- Database engine initialization (PostgreSQL)
- SQLAlchemy session factory
- Base class for all models

**mixins.py**:
- `UUIDPrimaryKeyMixin`: Provides UUID primary key to all models
- Common column definitions

### 3. Models Layer (`app/models/`)

Core business entities:

- **User**: Registered users with email, username, preferences
- **Valuation/ValuationJob**: Property valuation requests and processing queue
- **Subscription/SubscriptionPlan**: User subscriptions and available plans
- **Payment**: Payment transaction tracking
- **Feedback**: User feedback and reviews
- **Country**: Country-specific settings and pricing
- **ExchangeRate**: Currency conversion rates
- **Staff**: Administrative staff members
- **Inquiry**: Property inquiries and leads

### 4. Services Layer (`app/services/`)

Business logic abstraction:

- **AuthService**: User authentication, token generation, password management
- **UserService**: User CRUD operations and profile management
- **ValuationService**: Valuation report storage and retrieval
- **SubscriptionService**: Subscription lifecycle (create, renew, expire, cancel)
- **PricingService**: Price calculation based on country, currency, exchange rates
- **CurrencyResolver**: Multi-currency conversion and localization
- **ExchangeRateService**: Fetches and updates exchange rates
- **ValuationReportBuilder**: Constructs detailed valuation reports from LLM responses

### 5. Routes Layer (`app/routes/`)

API endpoint handlers organized by domain:

- **User Routes**: Registration, login, email verification, password reset
- **Valuation Routes**: Create/retrieve/list valuations
- **Subscription Routes**: View plans, manage subscriptions
- **Payment Routes**: Payment initiation and verification
- **Feedback Routes**: Submit and view feedback
- **Admin Routes**: User/subscription/valuation management

### 6. Schemas Layer (`app/schemas/`)

Pydantic models for:
- Request validation
- Response serialization
- Type hints and documentation

### 7. Celery Tasks (`app/tasks/`)

Asynchronous background jobs:

- **ValuationTasks**: Process valuation requests, integrate with LLM, save reports
- **SubscriptionTasks**: Check subscription expiry, send notifications, auto-renew
- **CurrencyTasks**: Update exchange rates, cache conversions
- **ExpireSubscriptionTask**: Mark expired subscriptions, trigger notifications

### 8. Middleware (`app/middleware/`)

**IPCountryMiddleware**:
- Detects user's country from IP address
- Stores country info in request context for use throughout request
- Used for localized pricing and currency selection

### 9. Utilities (`app/utils/`)

- **Email**: SMTP-based email sending with template rendering
- **PDFGenerator**: Creates professional valuation PDF reports
- **Logger**: Structured logging configuration
- **Phone**: Phone number validation and formatting
- **Maps**: Location/mapping utilities
- **Response**: Standard response formatting

---

## Database Models & Schema

### Users Table
```sql
users (
  id: UUID [PK],
  email: STRING [UNIQUE],
  username: STRING [UNIQUE],
  mobile_number: STRING,
  hashed_password: STRING,
  is_active: BOOLEAN,
  email_verified: BOOLEAN,
  email_verification_token: STRING,
  password_reset_token: STRING,
  country_code: STRING,
  created_at: DATETIME
)
```

### Subscription Plans Table
```sql
subscription_plans (
  id: UUID [PK],
  name: STRING,
  country_code: STRING,
  price: INTEGER (in cents),
  currency: STRING,
  max_reports: INTEGER,
  is_active: BOOLEAN,
  created_at: DATETIME
)
```

### User Subscriptions Table
```sql
user_subscriptions (
  id: UUID [PK],
  user_id: UUID [FK -> users],
  plan_id: UUID [FK -> subscription_plans],
  pricing_country_code: STRING,
  ip_country_code: STRING,
  payment_country_code: STRING,
  razorpay_order_id: STRING,
  razorpay_payment_id: STRING,
  razorpay_signature: STRING,
  payment_status: STRING (CREATED, AUTHORIZED, CAPTURED, FAILED, REFUNDED),
  start_date: DATETIME,
  end_date: DATETIME,
  reports_used: INTEGER,
  is_active: BOOLEAN,
  is_expired: BOOLEAN,
  auto_renew: BOOLEAN,
  cancelled_at: DATETIME
)
```

### Valuations Tables
```sql
valuation_jobs (
  id: UUID [PK],
  user_id: UUID [FK -> users],
  subscription_id: UUID,
  category: STRING,
  country_code: STRING,
  request_payload: JSON,
  status: STRING (queued, processing, completed, failed),
  valuation_id: STRING,
  error_message: STRING,
  created_at: DATETIME,
  updated_at: DATETIME
)

valuation_reports (
  id: UUID [PK],
  valuation_id: STRING [UNIQUE],
  user_id: UUID [FK -> users],
  subscription_id: UUID [FK -> user_subscriptions],
  category: STRING,
  country_code: STRING,
  user_fields: JSON,
  ai_response: JSON,
  report_context: JSON,
  created_at: DATETIME
)
```

### Countries Table
```sql
countries (
  id: UUID [PK],
  country_code: STRING [UNIQUE],
  country_name: STRING,
  currency_code: STRING,
  timezone: STRING,
  created_at: DATETIME
)
```

### Exchange Rates Table
```sql
exchange_rates (
  id: UUID [PK],
  from_currency: STRING,
  to_currency: STRING,
  rate: FLOAT,
  updated_at: DATETIME
)
```

### Staff Table
```sql
staff (
  id: UUID [PK],
  user_id: UUID [FK -> users],
  name: STRING,
  email: STRING [UNIQUE],
  phone: STRING,
  password: STRING,
  role: STRING,
  can_access_user: BOOLEAN,
  can_access_staff: BOOLEAN,
  can_access_dashboard: BOOLEAN,
  can_access_reports: BOOLEAN,
  can_access_subscriptions_plans: BOOLEAN,
  created_at: DATETIME
)
```

### Inquiries Table
```sql
inquiries (
  id: UUID [PK],
  type: STRING (CONTACT, SERVICE),
  first_name: STRING,
  last_name: STRING,
  email: STRING,
  phone_number: STRING,
  message: TEXT,
  services: JSON,
  created_at: DATETIME
)
```

---

## Authentication & Authorization

### User Authentication Flow

```
1. Registration
   ├─ POST /register (email, username, password, phone)
   ├─ Hash password with bcrypt
   ├─ Generate email verification token
   ├─ Send verification email
   └─ Store user in database (email_verified=false)

2. Email Verification
   ├─ User clicks verification link in email
   ├─ GET /verify-email?token=<token>
   ├─ Validate token signature and expiry
   ├─ Mark user email_verified=true
   └─ Redirect to login page

3. Login
   ├─ POST /login (email, password)
   ├─ Validate credentials (email_verified check)
   ├─ Generate JWT access token (short-lived)
   ├─ Generate JWT refresh token (long-lived)
   └─ Return tokens to client

4. Accessing Protected Endpoints
   ├─ Include "Authorization: Bearer <access_token>" header
   ├─ Middleware validates token signature & expiry
   ├─ If valid, extract user_id from token claims
   └─ Proceed with request

5. Token Refresh
   ├─ POST /refresh (using refresh_token)
   ├─ Validate refresh token
   ├─ Generate new access token
   └─ Return new tokens

6. Password Reset
   ├─ POST /forgot-password (email)
   ├─ Generate time-bound reset token
   ├─ Send reset link via email
   ├─ POST /reset-password (token, new_password)
   ├─ Validate token
   ├─ Hash and update password
   └─ User can now login with new password
```

### Admin Authentication

- Separate admin authentication endpoints
- Staff members create accounts with specific roles
- Super admin role for full system access
- Role-based access control on admin endpoints

### Token Structure

**Access Token** (JWT, ~15 min expiry):
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "exp": 1234567890,
  "type": "access"
}
```

**Refresh Token** (JWT, 7 days expiry):
```json
{
  "sub": "user_id",
  "exp": 1234567890,
  "type": "refresh"
}
```

---

## Key Workflows

### 1. Property Valuation Workflow

```
User Initiates Valuations
    │
    ├─ User submits valuation form via /valuations endpoint
    │  (property details, location, purpose, contact info)
    │
    ├─ Request Handler validates:
    │  ├─ User authentication
    │  ├─ Subscription active with available reports
    │  └─ Form data completeness
    │
    ├─ Create ValuationJob in database
    │  └─ Status: "queued"
    │
    ├─ Enqueue Celery task: process_valuation_task()
    │  └─ Return job_id to user immediately (async processing)
    │
    │
Celery Worker Processing
    │
    ├─ Pick up valuation_job from queue
    ├─ Update status: "processing"
    │
    ├─ Call LLM (Gemini or OpenAI)
    │  ├─ Format property data for LLM
    │  ├─ Send to LLM with system prompt
    │  └─ Receive structured analysis
    │
    ├─ Generate PDF Report
    │  ├─ Create formatted document
    │  ├─ Embed property analysis
    │  └─ Save to generated_reports/ folder
    │
    ├─ Save ValuationReport to database
    │  ├─ Store AI response (JSON)
    │  ├─ Store user input fields (JSON)
    │  ├─ Store report metadata
    │  └─ Increment subscription.reports_used
    │
    ├─ Update ValuationJob status: "completed"
    │
    ├─ Queue email notification task
    │  └─ Send report to user email
    │
    └─ Update job status in cache for real-time polling


User Retrieves Report
    │
    ├─ Poll /valuations/{job_id}/status for processing updates
    │
    ├─ Once completed, fetch /valuations/{job_id} to get report
    │
    ├─ Download PDF from generated_reports/
    │
    └─ View report in UI
```

### 2. Subscription & Payment Workflow

```
User Selects Plan
    │
    ├─ GET /subscriptions/plans
    │  ├─ Fetch plans for user's country (IP-detected)
    │  ├─ Apply exchange rate conversions if needed
    │  └─ Return localized pricing
    │
    ├─ User selects plan
    │
    └─ POST /subscriptions/create request


Create Order (Server-side)
    │
    ├─ Validate subscription plan
    | ├─ Apply auto-detected country price
    │ └─ Create UserSubscription record
    │    └─ Status: CREATED
    │
    ├─ Call Razorpay API
    │  ├─ Create order with amount, currency, description
    │  ├─ Save razorpay_order_id
    │  └─ Return order details to client
    │
    └─ Client receives order ID and amount


Client-side Payment
    │
    ├─ Open Razorpay payment modal
    ├─ User enters payment details
    ├─ Razorpay processes payment
    └─ Razorpay redirects with payment_id & signature


Payment Verification (Webhook)
    │
    ├─ Receive Razorpay webhook callback
    ├─ Verify signature matches (security)
    │
    ├─ If valid:
    │  ├─ Update UserSubscription
    │  │  ├─ payment_status: "CAPTURED"
    │  │  ├─ razorpay_payment_id: <payment_id>
    │  │  ├─ is_active: true
    │  │  ├─ start_date: NOW()
    │  │  └─ end_date: NOW() + plan_duration
    │  │
    │  └─ Enqueue email task
    │     └─ Send "Subscription Active" confirmation email
    │
    └─ If invalid:
       ├─ Payment automatically failed (webhook timeout)
       ├─ Send "Payment Failed" email
       └─ User can retry payment


Subscription Expiry (Scheduled Task)
    │
    ├─ Daily scheduled task checks for expiry
    ├─ If end_date <= NOW() and is_active=true:
    │  ├─ Set is_active=false
    │  ├─ Set is_expired=true
    │  │
    │  ├─ If auto_renew=true:
    │  │  ├─ Create new subscription with same plan
    │  │  └─ Initiate new payment
    │  │
    │  └─ Send "Subscription Expired" email
    │
    └─ Send expiry reminders 7 days before end_date
```

### 3. Multi-Currency & Country Localization

```
Request Arrives
    │
    ├─ IPCountryMiddleware extracts client IP
    ├─ Performs GeoIP lookup to determine country
    └─ Stores country_code in request context


Price Retrieval
    │
    ├─ GET /subscriptions/plans endpoint
    │
    ├─ For each subscription plan:
    │  ├─ Check if plan exists for user's country
    │  │
    │  ├─ If exists: use local price
    │  │
    │  └─ If not exists: apply currency conversion
    │     ├─ Get base currency price (e.g., USD)
    │     ├─ Fetch exchange_rate (USD → user_currency)
    │     ├─ Calculate: local_price = base_price * exchange_rate
    │     └─ Cache result for performance
    │
    └─ Return prices in user's local currency


Exchange Rate Updates
    │
    ├─ Scheduled daily task (00:00 UTC)
    ├─ Call external currency API
    ├─ Update exchange_rates table
    └─ Cache is invalidated, fresh rates used for next pricing call
```

### 4. Email Notification Workflow

```
Trigger Events
    │
    ├─ User registration → verification email
    ├─ Email verification → welcome email
    ├─ Password reset request → reset link email
    ├─ Subscription activated → confirmation email
    ├─ Subscription expiring (7 days) → reminder email
    ├─ Subscription expired → expiration email
    ├─ Valuation completed → report ready email
    └─ User feedback submitted → confirmation email


Task Enqueueing
    │
    ├─ Main application detects event
    ├─ Calls send_email_task.delay(email, template, context)
    └─ Task enqueued to Celery


Celery Worker Processing
    │
    ├─ Pick task from queue
    ├─ Load Jinja2 HTML template from templates/
    ├─ Render template with context data
    ├─ Connect to SMTP server
    ├─ Send email
    ├─ Log result
    └─ Mark task as completed
```

---

## Async Task Processing

### Celery Configuration

**Broker**: Redis (localhost:6379/0)
**Backend**: Redis (localhost:6379/1)
**Serialization**: JSON

### Scheduled Tasks (Celery Beat)

| Task | Schedule | Purpose |
|------|----------|---------|
| `expire_subscriptions_task` | Daily 00:00 UTC | Check and expire subscriptions |
| `send_expiry_reminders_task` | Daily 09:00 UTC | Send expiry reminder emails |
| `update_exchange_rates` | Daily 00:00 UTC | Update currency exchange rates |

### Task Queue Tasks

| Task | Trigger | Purpose |
|------|---------|---------|
| `process_valuation_task` | User submits valuation | Generate AI-powered valuation report |
| `send_email_task` | Various events | Send emails (verification, reset, notifications) |
| `update_exchange_rates_async` | On-demand | Refresh currency rates |
| `auto_renew_subscription_task` | Subscription expiry | Automatically renew if auto_renew=true |

### Task Status Tracking

```
Client polls: GET /tasks/{task_id}/status
    │
    ├─ Celery returns task state from Redis backend
    │  ├─ PENDING: Task not yet processed
    │  ├─ STARTED: Task processing
    │  ├─ SUCCESS: Task completed
    │  ├─ FAILURE: Task failed
    │  └─ RETRY: Task being retried
    │
    ├─ If SUCCESS: Return result data
    └─ If FAILURE: Return error message
```

---

## API Endpoints Structure

### User Endpoints

```
Authentication:
  POST   /register                  # User registration
  POST   /login                     # User login
  GET    /verify-email              # Email verification
  POST   /refresh                   # Refresh access token
  POST   /forgot-password           # Request password reset
  POST   /reset-password            # Reset password with token

Profile:
  GET    /users/me                  # Get current user profile
  PUT    /users/me                  # Update profile
  GET    /users/{id}                # Get user by ID (admin only)

Valuations:
  POST   /valuations                # Create new valuation
  GET    /valuations/{id}           # Get valuation report
  GET    /valuations                # List user's valuations
  GET    /valuations/{id}/status    # Get processing status
  GET    /valuations/{id}/pdf       # Download PDF report

Subscriptions:
  GET    /subscriptions/plans       # Get available plans
  GET    /subscriptions/me          # Get user's current subscription
  POST   /subscriptions/create      # Create new subscription
  PUT    /subscriptions/{id}        # Update subscription
  DELETE /subscriptions/{id}        # Cancel subscription

Payments:
  POST   /payments/verify           # Verify Razorpay payment

Feedback:
  POST   /feedback                  # Submit feedback
  GET    /feedback                  # Get own feedback

Inquiries:
  POST   /inquiries                 # Submit inquiry
  GET    /inquiries/{id}            # Get inquiry details
```

### Admin Endpoints

```
Admin Auth:
  POST   /admin/login               # Admin login
  POST   /admin/logout              # Admin logout
  POST   /admin/refresh             # Refresh admin token

User Management:
  GET    /admin/users               # List all users
  GET    /admin/users/{id}          # Get user details
  PUT    /admin/users/{id}          # Update user
  DELETE /admin/users/{id}          # Deactivate user
  POST   /admin/users/{id}/verify   # Manually verify email

Subscription Management:
  GET    /admin/subscriptions       # List all subscriptions
  GET    /admin/subscriptions/{id}  # Get subscription details
  PUT    /admin/subscriptions/{id}  # Update subscription
  POST   /admin/subscriptions/{id}/expire # Expire subscription
  POST   /admin/subscriptions/{id}/refund # Process refund

Plans:
  GET    /admin/plans               # List subscription plans
  POST   /admin/plans               # Create new plan
  PUT    /admin/plans/{id}          # Update plan
  DELETE /admin/plans/{id}          # Delete plan

Valuations:
  GET    /admin/valuations          # List all valuations
  GET    /admin/valuations/{id}     # Get valuation details
  DELETE /admin/valuations/{id}     # Delete valuation

Dashboard:
  GET    /admin/dashboard           # Dashboard metrics (users, revenue, etc.)
  GET    /admin/dashboard/charts    # Detailed analytics

Feedback:
  GET    /admin/feedback            # List all feedback
  GET    /admin/feedback/{id}       # Get feedback details
  PUT    /admin/feedback/{id}       # Update feedback status

Staff:
  GET    /admin/staff               # List staff members
  POST   /admin/staff               # Add staff member
  PUT    /admin/staff/{id}          # Update staff
  DELETE /admin/staff/{id}          # Remove staff

Countries & Pricing:
  GET    /admin/countries           # List countries
  POST   /admin/countries           # Add country
  PUT    /admin/countries/{id}      # Update country
  GET    /admin/exchange-rates      # View exchange rates
  POST   /admin/exchange-rates/sync # Sync rates with external service
```

---

## Admin Features

### Dashboard

Provides comprehensive analytics and monitoring:

- **User Metrics**: Total users, active users, new signups this month
- **Subscription Metrics**: Active subscriptions, expired, revenue
- **Valuation Metrics**: Total valuations, processing queue length, average generation time
- **Financial Metrics**: Monthly revenue, average subscription price, payment success rate
- **Charts**: Revenue trends, user growth, country distribution

### User Management

- View all users with filters and search
- Deactivate/activate user accounts
- Manually verify email (admin override)
- View user subscription history
- View user valuations

### Subscription & Plan Management

- Create/edit subscription plans with country-specific pricing
- Manage active subscriptions
- Issue refunds
- Auto-renewal settings
- Subscription cancellation and expiry

### Valuation Management

- Monitor valuation queue
- View completed valuations with AI responses
- Delete outdated valuations
- Track valuation generation performance metrics

### Feedback Management

- View all user feedback
- Mark feedback as resolved
- Respond to feedback
- Analytics on feedback categories

### Staff Management

- Add/remove administrative staff
- Assign roles (admin, moderator, analyst, etc.)
- Manage staff access levels

---

## Payment Integration

### Razorpay Integration

**Purpose**: Secure payment processing for subscription purchases

**Flow**:

1. **Server Creates Order**
   ```python
   # Backend
   response = razorpay_client.order.create(
       amount=price_in_paise,      # Amount in paise (100 paise = 1 rupee)
       currency='INR',             # or other currency
       receipt=receipt_id,
       description=plan_name
   )
   ```

2. **Client Opens Payment Modal**
   ```javascript
   // Frontend
   const options = {
       key: 'razorpay_key_id',
       amount: amount_in_paise,
       currency: 'INR',
       name: 'Property Valuation Platform',
       description: 'Subscription Purchase',
       order_id: razorpay_order_id,
       handler: function(response) {
           // Verify payment
       }
   };
   const rzp = new Razorpay(options);
   rzp.open();
   ```

3. **Payment Verification (Webhook)**
   ```python
   # Backend receives webhook from Razorpay
   # Verify signature: HMAC-SHA256(order_id + payment_id, secret)
   # If valid: Mark subscription active
   ```

4. **Payment Status Tracking**
   - CREATED: Order created, awaiting payment
   - AUTHORIZED: Payment authorized (for cards)
   - CAPTURED: Payment captured successfully
   - FAILED: Payment failed
   - REFUNDED: Refund processed

---

## Internationalization & Localization

### Multi-Country Support

**Automatic Detection**:
- Middleware detects client country via IP geolocation
- Country code stored in request context

**Country-Specific Data**:
- Subscription plans with localized pricing
- Currency selection per country
- Timezone handling
- Phone number formats

**Exchange Rate Management**:
- Daily exchange rate updates
- Multi-currency price calculation
- Cached conversion rates for performance

### Supported Localization

Currently supports:
- Multiple countries with unique pricing tiers
- Currency conversion (INR, USD, etc.)
- Country-specific SubscriptionPlans
- Automatic price display in user's local currency

---

## Logging & Monitoring

### Logging Configuration

**File**: `app/utils/logger_config.py`

**Features**:
- Structured logging with timestamps
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Log files: `app/logs/` directory
- Daily log files named like `app-2026-06-05.log`
- Retention cleanup to prevent old logs from filling disk space

**Log Levels**:
```python
logger.debug("Detailed information for diagnosis")
logger.info("General informational messages")
logger.warning("Warning messages for potential issues")
logger.error("Error messages for exceptions")
logger.critical("Critical issues requiring immediate action")
```

### Application Logging Points

- User authentication (login, registration, token generation)
- Database operations (CRUD, transactions)
- API requests (endpoint, parameters, response codes)
- Payment processing (order creation, verification)
- Async task execution (start, completion, failures)
- LLM API calls (request, response, latency)
- Email delivery (sent, bounced, failed)
- Error handling and stack traces

---

## Deployment & Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- SMTP server (for emails)
- Razorpay API credentials (for payments)
- Google Generative AI / OpenAI API keys (for LLM)

### Installation Steps

```bash
# 1. Clone repository
git clone <repository>
cd desktop_valuation-miral

# 2. Create virtual environment
python -m venv venv
source venv/Scripts/activate  # Windows
# or
source venv/bin/activate      # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Environment Configuration
# Create .env file with:
DATABASE_URL=postgresql://user:password@localhost/dbname
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
RAZORPAY_KEY_ID=your-key
RAZORPAY_KEY_SECRET=your-secret
OPENAI_API_KEY=your-key
GOOGLE_API_KEY=your-key
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your-email
SMTP_PASSWORD=your-password

# 5. Database Migration
alembic upgrade head

# 6. Create superuser (admin)
python app/scripts/create_superuser.py

# 7. Add countries
python app/scripts/add_country.py
```

### Running the Application

```bash
# Terminal 1: Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start Celery worker
celery -A app.celery_app worker -l info

# Terminal 3: Start Celery Beat (scheduler)
celery -A app.celery_app beat -l info

# Optional: Ngrok tunnel for webhooks
ngrok http 8000
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Production Deployment

**Recommended Setup**:
1. Use Gunicorn for FastAPI server (multiple workers)
2. Use Nginx as reverse proxy
3. PostgreSQL on dedicated database server
4. Redis on separate instance
5. Separate Celery worker servers
6. SSL/TLS certificate for HTTPS
7. Environment variables for secrets
8. Monitoring and logging aggregation

**Security Considerations**:
- Hash passwords with bcrypt (minimum 12 rounds)
- Use environment variables for API keys and secrets
- Enable CORS for trusted domains only
- Validate and sanitize all user inputs
- Implement rate limiting
- Use HTTPS for all communications
- Implement request signing for webhooks
- Regular security audits and dependency updates

---

## Key Technologies & Libraries Summary

| Technology | Purpose | Version |
|------------|---------|---------|
| FastAPI | Web framework | 0.124.4 |
| SQLAlchemy | ORM | Latest |
| PostgreSQL | Database | 12+ |
| Redis | Cache & broker | 6+ |
| Celery | Task queue | 5.6.0 |
| Pydantic | Data validation | Latest |
| Alembic | Migrations | 1.17.2 |
| BCrypt | Password hashing | 4.0.1 |
| python-jose | JWT tokens | Latest |
| Jinja2 | Templates | 3.1.6 |
| Razorpay | Payments | SDK |
| Google Gemini | LLM | SDK |
| OpenAI | LLM | 2.13.0 |
| ReportLab/WeasyPrint | PDF generation | Latest |

---

## Development Workflow

### Code Organization Principles

1. **Separation of Concerns**: Routes → Services → Models → Database
2. **Dependency Injection**: Use FastAPI `Depends()` for DI
3. **Error Handling**: Custom exceptions with meaningful messages
4. **Logging**: Log all important operations
5. **Validation**: Use Pydantic schemas for input validation
6. **Testing**: Write unit and integration tests
7. **Documentation**: Keep docstrings and comments updated

### Common Development Tasks

**Add New API Endpoint**:
1. Create schema in `app/schemas/`
2. Implement business logic in `app/services/`
3. Create route handler in `app/routes/`
4. Add database model if needed in `app/models/`
5. Write tests

**Add New Background Task**:
1. Create task function in `app/tasks/`
2. Define task in Celery configuration if scheduled
3. Queue task when event triggers
4. Monitor via Celery flower (optional)

**Add New Database Model**:
1. Create model in `app/models/`
2. Create migration: `alembic revision --autogenerate`
3. Run migration: `alembic upgrade head`
4. Create corresponding schema in `app/schemas/`
5. Implement service methods in `app/services/`

---

## Troubleshooting & Common Issues

### Celery Tasks Not Processing

**Symptoms**: Tasks stuck in "PENDING" state

**Solutions**:
1. Check Redis connection: `redis-cli ping`
2. Verify Celery worker is running
3. Check task imports in celery_app.py
4. Review Celery worker logs

### Database Connection Issues

**Symptoms**: SQLAlchemy connection errors

**Solutions**:
1. Verify PostgreSQL is running
2. Check DATABASE_URL in .env
3. Verify database credentials
4. Check firewall rules

### Email Delivery Failures

**Symptoms**: Emails not sent

**Solutions**:
1. Verify SMTP credentials in .env
2. Check email templates exist
3. Review Celery worker logs
4. Test SMTP connection manually

### Payment Verification Failing

**Symptoms**: Razorpay webhooks failing

**Solutions**:
1. Verify Razorpay credentials
2. Check webhook signature validation
3. Ensure ngrok tunnel is active for local testing
4. Review payment verification logs

---

## Conclusion

This Desktop Valuation Platform provides a complete, scalable solution for property valuation services with subscription management, payment processing, and comprehensive admin capabilities. The architecture follows best practices with clear separation of concerns, async processing for scalability, and extensible design for future enhancements.

For detailed API documentation, refer to `API_DOCUMENTATION.md`.
