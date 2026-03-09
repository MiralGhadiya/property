# Desktop Valuation Platform

**Desktop Valuation** is a comprehensive FastAPI-based platform that provides automated property valuation services with subscription management, payment processing, and administrative capabilities. The platform serves users across multiple countries with localized pricing, currency conversion, and property-specific valuations using AI/LLM integration.

## Key Features
- **User Authentication**: Email-based registration with verification and password management.
- **Property Valuations**: AI-powered property valuation generation with detailed PDF reports.
- **Subscription Management**: Multi-tier subscription plans with country-specific pricing.
- **Payment Processing**: Razorpay integration for secure payment handling.
- **Admin Dashboard**: Comprehensive admin panel for user, staff, subscription, inquiry, feedback, and valuation management.
- **Async Processing**: Celery-based background task processing for valuations and notifications.
- **Multi-Country Support**: Automatic IP-based country detection, localized pricing, and currency conversion.
- **Public Inquiries & Feedback**: Direct channels for users and visitors to communicate with administrators.

## Technology Stack
- **Backend**: FastAPI
- **Database**: PostgreSQL & SQLAlchemy (with Alembic for migrations)
- **Async Processing**: Celery & Redis
- **AI/LLM**: OpenAI
- **Payments**: Razorpay
- **PDF Generation**: Custom report builder

## Setup and Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- SMTP Server details
- API Keys: Razorpay, OpenAI

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository>
   cd property-main
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Create a `.env` file in the root directory and add the following:
   ```env
   root@desktopvaluation:/var/www/property# cat .env
   DATABASE_URL=postgresql://username:password@host/desktop_db
   REDIS_URL=redis://localhost:6379/0
   JWT_SECRET_KEY= *******
   ALGORITHM= "HS256"
   RAZORPAY_KEY_ID=rzp_teou******6KmZ
   RAZORPAY_KEY_SECRET=O6V******wW31ZTG
   OPENAI_API_KEY=sk
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   EMAIL_USER=miral.g.evenmore@gmail.com
   EMAIL_PASSWORD=ekm******cuyfka
   IPINFO_TOKEN=9a******c5bf7aa
   BASE_URL=http://192.168.1.90
   FRONTEND_URL=http://192.168.1.73:5173
   EXCHANGE_RATE_API_KEY=5cc66********aa6744
   GOOGLE_MAPS_API_KEY="AIzaSyB6UWT********_Gh4JgBsIYkg"
   GOOGLE_CLIENT_ID=339380282766-******.com
   ```

5. **Run Database Migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Initialize the Database:**
   ```bash
   python app/scripts/create_superuser.py
   python app/scripts/add_country.py
   ```

## Running the Application

Open separate terminals to run the various components of the architecture:


1. **Start the Celery worker (for background tasks like valuations and emails):**
   ```bash
   celery -A app.celery_app worker -l info
   ```

2. **Start the Celery Beat scheduler (for subscriptions expiry and daily exchange rates):**
   ```bash
   celery -A app.celery_app beat -l info
   ```

3. **Start the FastAPI server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```


## Documentation
- Detailed API Specs: see `API_DOCUMENTATION.md`
- Architecture & Models: see `PROJECT_ARCHITECTURE.md`
- Application Workflows: see `FLOW_DOCUMENTATION.md` and `PROJECT_FLOW_DOCUMENTATION.md`