<h1>TaskFlow — Smart Task Management System</h1>

<p>
A full-stack task management application built with Flask, PostgreSQL,
WebSockets, Pandas, and NumPy.
</p>

<p>
TaskFlow enables users to create, manage, update, and track tasks in
real time with live dashboard updates and analytics.
</p>

<h2>🚀 Features</h2>

<ul>
  <li>User Authentication (Register / Login / Logout)</li>
  <li>Secure session-based authentication</li>
  <li>Task CRUD operations</li>
  <li>Real-time task updates using WebSockets</li>
  <li>PostgreSQL database integration</li>
  <li>Analytics dashboard powered by Pandas + NumPy</li>
  <li>Responsive dark-themed UI</li>
  <li>RESTful API architecture</li>
  <li>Input validation and error handling</li>
  <li>Clean service-layer architecture</li>
</ul>

<h2>🛠️ Tech Stack</h2>

<h3>Backend</h3>
<ul>
  <li>Python</li>
  <li>Flask</li>
  <li>Flask-SQLAlchemy</li>
  <li>Flask-SocketIO</li>
  <li>PostgreSQL</li>
  <li>SQLAlchemy</li>
</ul>

<h3>Frontend</h3>
<ul>
  <li>HTML</li>
  <li>CSS</li>
  <li>JavaScript</li>
  <li>Socket.IO Client</li>
</ul>

<h3>Data & Analytics</h3>
<ul>
  <li>Pandas</li>
  <li>NumPy</li>
</ul>

<h3>Other Tools</h3>
<ul>
  <li>Eventlet</li>
  <li>python-dotenv</li>
  <li>psycopg2</li>
</ul>

<h2>📂 Project Structure</h2>

<pre>
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
</pre>

<h2>⚙️ Setup Instructions</h2>

<h3>1. Clone the Repository</h3>

<pre>
git clone &lt;your-repo-url&gt;
cd taskflow
</pre>

<h3>2. Create Virtual Environment</h3>

<h4>Windows</h4>

<pre>
python -m venv venv
venv\Scripts\activate
</pre>

<h4>Mac/Linux</h4>

<pre>
python3 -m venv venv
source venv/bin/activate
</pre>

<h3>3. Install Dependencies</h3>

<pre>
pip install -r requirements.txt
</pre>

<h3>4. Configure Environment Variables</h3>

<p>Create a <code>.env</code> file in the project root:</p>

<pre>
SECRET_KEY=your_secret_key

DATABASE_URL=postgresql://postgres:your_password@localhost:5432/flowdesk

SOCKETIO_ASYNC_MODE=eventlet
</pre>

<h3>5. Create PostgreSQL Database</h3>

<pre>
CREATE DATABASE flowdesk;
</pre>

<h3>6. Run Database Schema</h3>

<pre>
psql -U postgres -d flowdesk -f schema.sql
</pre>

<h3>7. Start the Server</h3>

<pre>
python run.py
</pre>

<p><strong>Application runs at:</strong></p>

<pre>
http://localhost:5000
</pre>

<h2>📡 API Endpoints</h2>

<h3>Authentication</h3>

<table border="1" cellpadding="8" cellspacing="0">
  <tr>
    <th>Method</th>
    <th>Endpoint</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>POST</td>
    <td>/auth/api/register</td>
    <td>Register user</td>
  </tr>
  <tr>
    <td>POST</td>
    <td>/auth/api/login</td>
    <td>Login user</td>
  </tr>
  <tr>
    <td>POST</td>
    <td>/auth/api/logout</td>
    <td>Logout user</td>
  </tr>
</table>

<br>

<h3>Tasks</h3>

<table border="1" cellpadding="8" cellspacing="0">
  <tr>
    <th>Method</th>
    <th>Endpoint</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>GET</td>
    <td>/api/tasks</td>
    <td>Get all tasks</td>
  </tr>
  <tr>
    <td>GET</td>
    <td>/api/tasks/&lt;id&gt;</td>
    <td>Get single task</td>
  </tr>
  <tr>
    <td>POST</td>
    <td>/api/tasks</td>
    <td>Create task</td>
  </tr>
  <tr>
    <td>PUT</td>
    <td>/api/tasks/&lt;id&gt;</td>
    <td>Update task</td>
  </tr>
  <tr>
    <td>DELETE</td>
    <td>/api/tasks/&lt;id&gt;</td>
    <td>Delete task</td>
  </tr>
</table>

<br>

<h3>Analytics</h3>

<table border="1" cellpadding="8" cellspacing="0">
  <tr>
    <th>Method</th>
    <th>Endpoint</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>GET</td>
    <td>/api/analytics</td>
    <td>Task analytics</td>
  </tr>
</table>

<h2>📊 Analytics Engine</h2>

<p>The analytics module uses Pandas and NumPy to generate:</p>

<ul>
  <li>Task completion statistics</li>
  <li>Priority distribution</li>
  <li>Daily task trends</li>
  <li>Productivity score</li>
  <li>Status breakdown percentages</li>
</ul>

<h3>Productivity Score Formula</h3>

<pre>
counts  = np.array([completed, in_progress, pending])
weights = np.array([1.0, 0.5, 0.0])

score = np.dot(counts, weights) / total * 100
</pre>

<h2>🔒 Security Features</h2>

<ul>
  <li>Password hashing using Werkzeug</li>
  <li>Session-based authentication</li>
  <li>IDOR protection</li>
  <li>Input validation</li>
  <li>Protected API routes</li>
  <li>Environment-variable-based secrets</li>
</ul>

<h2>🧠 Architecture Highlights</h2>

<h3>Layered Backend Design</h3>

<ul>
  <li>Routes → Handle HTTP requests</li>
  <li>Services → Business logic</li>
  <li>Models → Database layer</li>
  <li>Utils → Reusable helpers</li>
</ul>

<h3>Database Design</h3>

<ul>
  <li>PostgreSQL ENUM types</li>
  <li>Foreign key constraints</li>
  <li>Indexed queries</li>
  <li>Auto-updating timestamps via triggers</li>
  <li>Cascade delete relationships</li>
</ul>

<h2>📸 Screenshots</h2>

<p>
<img src="image.png" width="800">
</p>

<p>
<img src="image-1.png" width="800">
</p>

<p>
<img src="image-2.png" width="800">
</p>

<p>
<img src="image-3.png" width="800">
</p>

<h2>🌐 Real-Time Updates</h2>

<p>
TaskFlow uses Flask-SocketIO for real-time task synchronization.
</p>

<p>Whenever a task is:</p>

<ul>
  <li>Created</li>
  <li>Updated</li>
  <li>Deleted</li>
</ul>

<p>
All connected clients receive instant updates without refreshing the page.
</p>

<h2>💡 Future Improvements</h2>

<ul>
  <li>JWT authentication</li>
  <li>Drag-and-drop tasks</li>
  <li>Due dates & reminders</li>
  <li>Docker deployment</li>
  <li>Unit testing</li>
  <li>Role-based access control</li>
  <li>Email notifications</li>
</ul>

<h2>👨‍💻 Author</h2>

<p>
<strong>Riza Mukhaddam Khaji</strong>
</p>

<p>
Built as a full-stack internship project using Flask, PostgreSQL,
WebSockets, Pandas, and NumPy.
</p>

<h2>📜 License</h2>

<p>
This project is for educational and internship evaluation purposes.
</p>
