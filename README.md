# CS Ticket System

A modern, asynchronous Customer Support Ticket Management System built with FastAPI, SQLAlchemy, and PostgreSQL.

## 🌟 Features

### Technical Stack
- **Backend**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Async Support**: Full async database operations
- **Authentication**: Token-based authentication
- **Migration**: Alembic for database schema management

### Functional Features
- Multi-role user system (Customer and CS Representative)
- Ticket creation with rich metadata
- Image attachment support
- Real-time ticket status tracking
- Comprehensive ticket response system

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL
- pip
- virtualenv (recommended)

### Installation Steps

1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/cs_ticket_system.git
cd cs_ticket_system
```

2. **Create Virtual Environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

4. **Database Setup**
- Create a PostgreSQL database
- Update `.env` file with your database credentials
```bash
# Example .env configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/cs_tickets
SECRET_KEY=your_secret_key
```

5. **Database Migrations**
```bash
# Initialize Alembic (if not already done)
# alembic init alembic

# Generate initial migration
# alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

6. **Run the Application**
```bash
# Development mode with hot reload
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📘 API Documentation

Access API documentation when the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔐 Authentication Endpoints

- `POST /token`: Login and obtain access token
- `POST /register`: Register new user


## 🎫 Ticket Management Endpoints

- `POST /api/tickets/`: Create a new ticket
- `GET /api/tickets/`: Retrieve list of tickets
- `GET /api/tickets/{ticket_id}`: Get details of a specific ticket
- `GET /api/tickets/{ticket_id}/messages`: Retrieve messages for a specific ticket
- `POST /api/tickets/{ticket_id}/messages/`: Create a new message for a ticket
- `PATCH /api/tickets/{ticket_id}/close`: Close a ticket
- `PATCH /api/tickets/{ticket_id}/reopen`: Reopen a ticket

### Ticket Responses
- `DELETE /api/messages/{message_id}/attachments/{attachment_id}`: Delete a message attachment

## 🛠 Development


## 📦 Dependencies
- FastAPI
- SQLAlchemy
- Alembic
- Pydantic
- PostgreSQL
- Uvicorn
- python-jose
- passlib
- python-multipart

## 🤝 Contributing
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Contact
Vishal Agrawal - vishal18593@gmail.com

Project Link: [https://github.com/bazinga012/cs_ticket_system](https://github.com/bazinga012/cs_ticket_system)
