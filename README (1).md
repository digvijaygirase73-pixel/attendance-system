# 📋 AttendancePro — Student Attendance Management System

A full-stack web application built with **Python Flask**, **SQLite**, and **REST APIs** for managing student attendance in schools and colleges.

---

## 🚀 Features

- 🔐 **Login / Logout** with role-based access (Admin & Teacher)
- 👥 **Student Management** — Add, Edit, Delete, Search students
- ✅ **Mark Attendance** — by date and division with one click
- 📊 **Reports & Analytics** — with date filter and progress bars
- ⬇ **CSV Export** — download attendance report as Excel-compatible file
- 🌐 **External Holiday API** — live public holiday data from Nager.Date
- 🔌 **REST APIs** — JSON endpoints for students, attendance, and stats
- 🗄 **SQLite Database** — with SQLAlchemy ORM

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python Flask |
| Database | SQLite + Flask-SQLAlchemy |
| Frontend | HTML, CSS, Jinja2 Templates |
| Authentication | Flask Session + Werkzeug Password Hashing |
| External API | Nager.Date Public Holiday API |
| CSV Export | Python csv module |
| Deployment | Render / PythonAnywhere |

---

## 📁 Project Structure

```
attendance-system/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── attendance.db           # SQLite database (auto-created)
└── templates/
    ├── base.html           # Base layout with sidebar
    ├── login.html          # Login page
    ├── dashboard.html      # Dashboard with stats
    ├── attendance.html     # Mark attendance page
    ├── students.html       # Students list
    ├── student_form.html   # Add/Edit student form
    ├── reports.html        # Reports & analytics
    ├── teachers.html       # Manage teachers (Admin only)
    ├── teacher_form.html   # Add/Edit teacher form
    └── holidays.html       # Holiday calendar (External API)
```

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1 — Clone the repository
```bash
git clone https://github.com/akgfxdesign/attendance-system.git
cd attendance-system
```

### Step 2 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3 — Run the application
```bash
python app.py
```

### Step 4 — Open in browser
```
http://127.0.0.1:5000
```

---

## 🔑 Demo Credentials

| Role | Email | Password |
|---|---|---|
| Admin | admin@school.com | admin123 |
| Teacher | teacher@school.com | teacher123 |

---

## 🗄 Database Models

### User
```python
id, name, email, password (hashed), role (admin/teacher)
```

### Student
```python
id, name, roll_no, division, email, created_at
```

### AttendanceRecord
```python
id, student_id, date, status (Present/Absent), marked_by
```

---

## 🔌 REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/students` | Get all students as JSON |
| GET | `/api/attendance/<date>` | Get attendance by date (YYYY-MM-DD) |
| GET | `/api/dashboard/stats` | Get today's attendance stats |
| GET | `/api/external/holidays` | Fetch live holidays from external API |

### Example API Response — `/api/students`
```json
[
  {
    "id": 1,
    "name": "Aarav Shah",
    "roll_no": "01",
    "division": "4AI4",
    "email": "student01@school.com"
  }
]
```

### Example API Response — `/api/dashboard/stats`
```json
{
  "total_students": 8,
  "present_today": 6,
  "absent_today": 2,
  "total_records": 48
}
```

---

## 🌐 External API Integration

This project integrates with the **Nager.Date Public Holiday API**:

- **API URL:** `https://date.nager.at/api/v3/publicholidays/{year}/{country}`
- **Type:** REST API (HTTP GET)
- **Authentication:** None required (free public API)
- **Data Format:** JSON
- **Usage:** Fetch live public holidays for 100+ countries

```python
response = requests.get(
    "https://date.nager.at/api/v3/publicholidays/2025/US",
    headers={"Accept": "application/json"}
)
holidays = response.json()
```

---

## 👑 Role-Based Access Control

| Feature | Teacher | Admin |
|---|---|---|
| Mark Attendance | ✅ | ✅ |
| View Students | ✅ read-only | ✅ |
| Add/Edit/Delete Students | ❌ | ✅ |
| View Reports | ✅ | ✅ |
| Export CSV | ❌ | ✅ |
| Manage Teachers | ❌ | ✅ |
| API Explorer | ❌ | ✅ |

---

## 📊 Reports Features

- **All Time** — Overall attendance summary
- **Single Date** — Attendance for a specific day
- **Date Range** — Attendance between two dates
- **Progress Bars** — Visual attendance percentage
- **Below 75% Alert** — Highlights students with low attendance
- **CSV Export** — Download as spreadsheet

---

## 🚀 Deployment

### Deploy on Render (Free)

1. Push code to GitHub
2. Go to [render.com](https://render.com)
3. New → Web Service → Connect GitHub repo
4. Set **Build Command:** `pip install -r requirements.txt`
5. Set **Start Command:** `gunicorn app:app`
6. Select **Free** instance
7. Click **Create Web Service**

---

## 👨‍💻 Developer Info

| Field | Details |
|---|---|
| **Name** | Ritesh Jitendra Saner |
| **Roll No.** | 34 |
| **Enrollment No.** | 2403031240020 |
| **Division** | 4AI4 |
| **Project** | Attendance Management System |
| **Framework** | Python Flask |
| **Database** | SQLite with SQLAlchemy ORM |
| **Academic Year** | 2026-27 |

---

## 📝 Requirements

```
flask
flask-sqlalchemy
werkzeug
requests
gunicorn
```

---

## 📄 License

This project is built for academic purposes.
