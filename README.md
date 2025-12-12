# Fundora

**Connecting Startups with Investors**

Fundora is a web-based discovery platform that bridges the funding visibility gap in the Philippine startup ecosystem. By centralizing startup profiles and providing investors with evaluation tools, Fundora facilitates meaningful connections between early-stage founders and angel investors.

---

## Live Demo

**Platform URL:** [https://fundora-fe.onrender.com]

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Deployment](#deployment)
- [Test Accounts](#test-accounts)

---

## Features

### For Investors
- 🔍 Browse and filter startups by industry, funding needs, and risk level
- 📊 Investment calculator with IRR (Internal Rate of Return) analysis
- ⭐ Watchlist to save interesting startups
- ⚖️ Side-by-side startup comparison tool
- 📧 Direct access to founder contact information

### For Startups
- 📝 Create detailed profiles with financials and pitch decks
- 💼 Display contact information to attract investors
- 📈 Showcase funding needs and business metrics
- 🎯 Get discovered by active angel investors
---

## 🛠 Tech Stack

### Frontend
- **HTML5** - Markup structure
- **CSS3** - Styling and responsive design
- **JavaScript (ES6+)** - Client-side interactivity and API integration

### Backend
- **Python 3.11+** - Programming language
- **Django 4.2+** - Web framework
- **Django REST Framework (DRF) 3.14+** - API development
- **PostgreSQL** - Database (production)
- **SQLite** - Database (development)

### Deployment
- **Render** - Cloud platform for both frontend and backend hosting

### Additional Tools
- **Git** - Version control
- **pip** - Python package management

---

## 🚦 Getting Started

### Prerequisites

Ensure you have the following installed:
- Python 3.11 or higher
- pip (Python package manager)
- Git
- A modern web browser

### Installation

#### 1. Clone the Repository

```bash
# Backend
git clone https://github.com/Pauljesmarc/Fundora_BE.git

# Frontend
git clone https://github.com/Pauljesmarc/Fundora_FE.git
```

#### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

The backend API will be available at `http://localhost:8000`

#### 3. Frontend Setup

```bash
# Navigate to frontend directory (from project root)
cd frontend

# If using a simple HTTP server:
python -m http.server 8080

# Or use any other local server solution
```

The frontend will be available at `http://localhost:8080`

#### 4. Environment Variables

Create a `.env` file in the backend directory:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3

# For production (Render):
# DATABASE_URL=postgresql://user:password@host:port/database
```

---

## Test Accounts

Use these credentials to explore different user experiences:

### Investor Account
```
Email: JaneDoe@gmail.com
Password: Janedoe123
```

**Access:** Browse startups, use investment calculator, manage watchlist

### Startup Account
```
Email: JohnDoe@gmail.com
Password: Johndoe123
```

**Access:** Create/edit startup profile, view investor interest, update financials

> **Note:** These are demo accounts for testing purposes only. Do not use real sensitive information.
