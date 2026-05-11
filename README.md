TaskFlow — Smart Task Management System

A full-stack task management application built with Flask, PostgreSQL, WebSockets, Pandas, and NumPy.

TaskFlow enables users to create, manage, update, and track tasks in real time with live dashboard updates and analytics.

🚀 Features
User Authentication (Register / Login / Logout)
Secure session-based authentication
Task CRUD operations
Real-time task updates using WebSockets
PostgreSQL database integration
Analytics dashboard powered by Pandas + NumPy
Responsive dark-themed UI
RESTful API architecture
Input validation and error handling
Clean service-layer architecture
🛠️ Tech Stack
Backend
Python
Flask
Flask-SQLAlchemy
Flask-SocketIO
PostgreSQL
SQLAlchemy
Frontend
HTML
CSS
JavaScript
Socket.IO Client
Data & Analytics
Pandas
NumPy
Other Tools
Eventlet
python-dotenv
psycopg2
📂 Project Structure
taskflow/
│
├── app/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── utils/
│   └── websocket/
│
├── analytics/
├── config/
├── static/
├── templates/
│
├── schema.sql
├── requirements.txt
├── run.py
└── README.md
⚙️ Setup Instructions
1. Clone the Repository
git clone <your-repo-url>
cd taskflow
2. Create Virtual Environment
Windows
python -m venv venv
venv\Scripts\activate
Mac/Linux
python3 -m venv venv
source venv/bin/activate
3. Install Dependencies
pip install -r requirements.txt
4. Configure Environment Variables

Create a .env file in the project root:

SECRET_KEY=your_secret_key

DATABASE_URL=postgresql://postgres:your_password@localhost:5432/flowdesk

SOCKETIO_ASYNC_MODE=eventlet
5. Create PostgreSQL Database
CREATE DATABASE flowdesk;
6. Run Database Schema
psql -U postgres -d flowdesk -f schema.sql
7. Start the Server
python run.py

Application runs at:

http://localhost:5000
📡 API Endpoints
Authentication
Method	Endpoint	Description
POST	/auth/api/register	Register user
POST	/auth/api/login	Login user
POST	/auth/api/logout	Logout user
Tasks
Method	Endpoint	Description
GET	/api/tasks	Get all tasks
GET	/api/tasks/<id>	Get single task
POST	/api/tasks	Create task
PUT	/api/tasks/<id>	Update task
DELETE	/api/tasks/<id>	Delete task
Analytics
Method	Endpoint	Description
GET	/api/analytics	Task analytics
📊 Analytics Engine

The analytics module uses Pandas and NumPy to generate:

Task completion statistics
Priority distribution
Daily task trends
Productivity score
Status breakdown percentages
Productivity Score Formula
counts  = np.array([completed, in_progress, pending])
weights = np.array([1.0, 0.5, 0.0])

score = np.dot(counts, weights) / total * 100
🔒 Security Features
Password hashing using Werkzeug
Session-based authentication
IDOR protection
Input validation
Protected API routes
Environment-variable-based secrets
🧠 Architecture Highlights
Layered Backend Design
Routes → Handle HTTP requests
Services → Business logic
Models → Database layer
Utils → Reusable helpers
Database Design
PostgreSQL ENUM types
Foreign key constraints
Indexed queries
Auto-updating timestamps via triggers
Cascade delete relationships
📸 Screenshots
![alt text](image.png)
![alt text](image-1.png)
![alt text](image-2.png)
![alt text](image-3.png)

🌐 Real-Time Updates

FlowDesk uses Flask-SocketIO for real-time task synchronization.

Whenever a task is:

Created
Updated
Deleted

all connected clients receive instant updates without refreshing the page.

💡 Future Improvements
JWT authentication
Drag-and-drop tasks
Due dates & reminders
Docker deployment
Unit testing
Role-based access control
Email notifications
👨‍💻 Author

Riza Mukhaddam Khaji

Built as a full-stack internship project using Flask, PostgreSQL, WebSockets, Pandas, and NumPy.

📜 License

This project is for educational and internship evaluation purposes.