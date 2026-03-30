from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime
import csv, io
import requests as ext_requests

app = Flask(__name__)
app.secret_key = "attendance_secret_key_2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///attendance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}

# ─────────────────────────────────────────
#  MODELS
# ─────────────────────────────────────────

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20), default="teacher")  # admin / teacher

class Student(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    roll_no    = db.Column(db.String(20), unique=True, nullable=False)
    division   = db.Column(db.String(20), nullable=False)
    email      = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    records    = db.relationship("AttendanceRecord", backref="student", lazy=True, cascade="all, delete-orphan")

class AttendanceRecord(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    date       = db.Column(db.Date, nullable=False)
    status     = db.Column(db.String(10), nullable=False)
    marked_by  = db.Column(db.Integer, db.ForeignKey("user.id"))
    __table_args__ = (db.UniqueConstraint("student_id", "date"),)

# ─────────────────────────────────────────
#  AUTH DECORATORS
# ─────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("⛔ Admin access required.", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
#  AUTH ROUTES
# ─────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            session["name"]    = user.name
            session["role"]    = user.role
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────

@app.route("/dashboard")
@login_required
def dashboard():
    today         = date.today()
    total_students= Student.query.count()
    present_today = AttendanceRecord.query.filter_by(date=today, status="Present").count()
    absent_today  = AttendanceRecord.query.filter_by(date=today, status="Absent").count()
    total_records = AttendanceRecord.query.count()
    recent_records= (
        db.session.query(AttendanceRecord, Student)
        .join(Student).order_by(AttendanceRecord.id.desc()).limit(8).all()
    )
    return render_template("dashboard.html",
        total_students=total_students, present_today=present_today,
        absent_today=absent_today, total_records=total_records,
        recent_records=recent_records, today=today,
    )

# ─────────────────────────────────────────
#  STUDENTS  (Admin: full CRUD | Teacher: read-only)
# ─────────────────────────────────────────

@app.route("/students")
@login_required
def students():
    q     = request.args.get("q", "")
    div   = request.args.get("division", "")
    query = Student.query
    if q:
        query = query.filter(Student.name.ilike(f"%{q}%") | Student.roll_no.ilike(f"%{q}%"))
    if div:
        query = query.filter_by(division=div)
    all_students = query.order_by(Student.name).all()
    divisions    = [r[0] for r in db.session.query(Student.division).distinct().all()]
    return render_template("students.html", students=all_students, divisions=divisions, q=q, div=div)

@app.route("/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        roll_no  = request.form.get("roll_no", "").strip()
        division = request.form.get("division", "").strip()
        email    = request.form.get("email", "").strip()
        if Student.query.filter_by(roll_no=roll_no).first():
            flash("Roll number already exists.", "error")
        else:
            db.session.add(Student(name=name, roll_no=roll_no, division=division, email=email))
            db.session.commit()
            flash(f"Student '{name}' added successfully.", "success")
            return redirect(url_for("students"))
    return render_template("student_form.html", student=None)

@app.route("/students/edit/<int:sid>", methods=["GET", "POST"])
@admin_required
def edit_student(sid):
    student = Student.query.get_or_404(sid)
    if request.method == "POST":
        student.name     = request.form.get("name", "").strip()
        student.roll_no  = request.form.get("roll_no", "").strip()
        student.division = request.form.get("division", "").strip()
        student.email    = request.form.get("email", "").strip()
        db.session.commit()
        flash("Student updated.", "success")
        return redirect(url_for("students"))
    return render_template("student_form.html", student=student)

@app.route("/students/delete/<int:sid>", methods=["POST"])
@admin_required
def delete_student(sid):
    student = Student.query.get_or_404(sid)
    db.session.delete(student)
    db.session.commit()
    flash(f"Student '{student.name}' deleted.", "success")
    return redirect(url_for("students"))

# ─────────────────────────────────────────
#  ATTENDANCE  (Both roles can mark)
# ─────────────────────────────────────────

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    selected_date = request.args.get("date", str(date.today()))
    division      = request.args.get("division", "")
    try:
        sel_date = date.fromisoformat(selected_date)
    except ValueError:
        sel_date = date.today()

    query = Student.query
    if division:
        query = query.filter_by(division=division)
    all_students = query.order_by(Student.name).all()
    existing     = {r.student_id: r.status for r in AttendanceRecord.query.filter_by(date=sel_date).all()}
    divisions    = [r[0] for r in db.session.query(Student.division).distinct().all()]

    if request.method == "POST":
        for s in all_students:
            status = request.form.get(f"status_{s.id}", "Absent")
            rec = AttendanceRecord.query.filter_by(student_id=s.id, date=sel_date).first()
            if rec:
                rec.status = status
            else:
                db.session.add(AttendanceRecord(
                    student_id=s.id, date=sel_date,
                    status=status, marked_by=session["user_id"]
                ))
        db.session.commit()
        flash(f"Attendance saved for {sel_date.strftime('%d %b %Y')}.", "success")
        return redirect(url_for("attendance", date=selected_date, division=division))

    return render_template("attendance.html",
        students=all_students, existing=existing,
        selected_date=selected_date, divisions=divisions, division=division,
    )

# ─────────────────────────────────────────
#  REPORTS  (Both roles: view | Admin only: export CSV)
#  Filter by date range or specific date
# ─────────────────────────────────────────

@app.route("/reports")
@login_required
def reports():
    # Date filter params
    filter_type  = request.args.get("filter", "all")   # all | date | range
    single_date  = request.args.get("single_date", "")
    date_from    = request.args.get("date_from", "")
    date_to      = request.args.get("date_to", "")
    div_filter   = request.args.get("division", "")

    students_q = Student.query
    if div_filter:
        students_q = students_q.filter_by(division=div_filter)
    all_students = students_q.order_by(Student.name).all()
    divisions    = [r[0] for r in db.session.query(Student.division).distinct().all()]

    # Get all distinct dates that have records
    all_dates = [r[0] for r in db.session.query(AttendanceRecord.date).distinct().order_by(AttendanceRecord.date.desc()).all()]

    report = []
    date_label = "All Time"

    for s in all_students:
        rec_q = AttendanceRecord.query.filter_by(student_id=s.id)

        if filter_type == "date" and single_date:
            try:
                d = date.fromisoformat(single_date)
                rec_q = rec_q.filter_by(date=d)
                date_label = d.strftime("%d %b %Y")
            except ValueError:
                pass
        elif filter_type == "range" and date_from and date_to:
            try:
                df = date.fromisoformat(date_from)
                dt = date.fromisoformat(date_to)
                rec_q = rec_q.filter(AttendanceRecord.date >= df, AttendanceRecord.date <= dt)
                date_label = f"{df.strftime('%d %b')} – {dt.strftime('%d %b %Y')}"
            except ValueError:
                pass

        records = rec_q.all()
        total   = len(records)
        present = sum(1 for r in records if r.status == "Present")
        absent  = total - present
        pct     = round((present / total * 100) if total else 0, 1)
        report.append({"student": s, "total": total, "present": present, "absent": absent, "pct": pct})

    report.sort(key=lambda x: x["pct"], reverse=True)
    return render_template("reports.html",
        report=report, date_label=date_label,
        filter_type=filter_type, single_date=single_date,
        date_from=date_from, date_to=date_to,
        all_dates=all_dates, divisions=divisions, div_filter=div_filter,
    )

@app.route("/reports/export")
@admin_required
def export_csv():
    filter_type = request.args.get("filter", "all")
    single_date = request.args.get("single_date", "")
    date_from   = request.args.get("date_from", "")
    date_to     = request.args.get("date_to", "")

    students = Student.query.order_by(Student.name).all()
    output   = io.StringIO()
    writer   = csv.writer(output)
    writer.writerow(["Roll No", "Name", "Division", "Total Days", "Present", "Absent", "Attendance %"])

    for s in students:
        rec_q = AttendanceRecord.query.filter_by(student_id=s.id)
        if filter_type == "date" and single_date:
            try:
                rec_q = rec_q.filter_by(date=date.fromisoformat(single_date))
            except ValueError:
                pass
        elif filter_type == "range" and date_from and date_to:
            try:
                rec_q = rec_q.filter(
                    AttendanceRecord.date >= date.fromisoformat(date_from),
                    AttendanceRecord.date <= date.fromisoformat(date_to)
                )
            except ValueError:
                pass
        records = rec_q.all()
        total   = len(records)
        present = sum(1 for r in records if r.status == "Present")
        absent  = total - present
        pct     = round((present / total * 100) if total else 0, 1)
        writer.writerow([s.roll_no, s.name, s.division, total, present, absent, f"{pct}%"])

    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance_report.csv"})

# ─────────────────────────────────────────
#  TEACHER MANAGEMENT  (Admin only)
# ─────────────────────────────────────────

@app.route("/teachers")
@admin_required
def teachers():
    all_teachers = User.query.filter_by(role="teacher").order_by(User.name).all()
    return render_template("teachers.html", teachers=all_teachers)

@app.route("/teachers/add", methods=["GET", "POST"])
@admin_required
def add_teacher():
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "error")
        else:
            db.session.add(User(name=name, email=email,
                                password=generate_password_hash(password), role="teacher"))
            db.session.commit()
            flash(f"Teacher '{name}' added.", "success")
            return redirect(url_for("teachers"))
    return render_template("teacher_form.html", teacher=None)

@app.route("/teachers/edit/<int:tid>", methods=["GET", "POST"])
@admin_required
def edit_teacher(tid):
    teacher = User.query.get_or_404(tid)
    if request.method == "POST":
        teacher.name  = request.form.get("name", "").strip()
        teacher.email = request.form.get("email", "").strip()
        new_pass = request.form.get("password", "").strip()
        if new_pass:
            teacher.password = generate_password_hash(new_pass)
        db.session.commit()
        flash("Teacher updated.", "success")
        return redirect(url_for("teachers"))
    return render_template("teacher_form.html", teacher=teacher)

@app.route("/teachers/delete/<int:tid>", methods=["POST"])
@admin_required
def delete_teacher(tid):
    teacher = User.query.get_or_404(tid)
    if teacher.id == session["user_id"]:
        flash("Cannot delete your own account.", "error")
        return redirect(url_for("teachers"))
    db.session.delete(teacher)
    db.session.commit()
    flash(f"Teacher '{teacher.name}' deleted.", "success")
    return redirect(url_for("teachers"))

# ─────────────────────────────────────────
#  REST APIs
# ─────────────────────────────────────────

@app.route("/api/students")
@login_required
def api_students():
    students = Student.query.order_by(Student.name).all()
    return jsonify([{"id": s.id, "name": s.name, "roll_no": s.roll_no,
                     "division": s.division, "email": s.email} for s in students])

@app.route("/api/attendance/<string:date_str>")
@login_required
def api_attendance_by_date(date_str):
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Use YYYY-MM-DD format"}), 400
    records = db.session.query(AttendanceRecord, Student).join(Student).filter(AttendanceRecord.date == d).all()
    return jsonify([{"name": s.name, "roll_no": s.roll_no, "division": s.division,
                     "status": r.status, "date": str(r.date)} for r, s in records])

@app.route("/api/dashboard/stats")
@login_required
def api_dashboard_stats():
    today = date.today()
    return jsonify({
        "total_students": Student.query.count(),
        "present_today":  AttendanceRecord.query.filter_by(date=today, status="Present").count(),
        "absent_today":   AttendanceRecord.query.filter_by(date=today, status="Absent").count(),
        "total_records":  AttendanceRecord.query.count(),
    })

# ─────────────────────────────────────────
#  SEED DB
# ─────────────────────────────────────────

def seed_db():
    if User.query.count() == 0:
        db.session.add_all([
            User(name="Admin", email="admin@school.com",
                 password=generate_password_hash("admin123"), role="admin"),
            User(name="Mr. Teacher", email="teacher@school.com",
                 password=generate_password_hash("teacher123"), role="teacher"),
        ])
    if Student.query.count() == 0:
        for name, roll, div in [
            ("Aarav Shah","01","4AI4"),("Priya Mehta","02","4AI4"),
            ("Rohan Patel","03","4AI4"),("Sneha Desai","04","4AI4"),
            ("Karan Joshi","05","4AI4"),("Meera Nair","06","4AI4"),
            ("Dev Sharma","07","4AI4"),("Pooja Verma","08","4AI4"),
        ]:
            db.session.add(Student(name=name, roll_no=roll, division=div,
                                   email=f"student{roll}@school.com"))
    db.session.commit()

with app.app_context():
    db.create_all()
    seed_db()

# ─────────────────────────────────────────
#  EXTERNAL API — Nager.Date Holiday API
#  https://date.nager.at/api/v3/publicholidays/{year}/{country}
#  100% FREE — No API key needed — Works for India & 100+ countries
# ─────────────────────────────────────────

NAGER_API_URL = "https://date.nager.at/api/v3/publicholidays"

def fetch_holidays_from_api(country, year, month=None, day=None):
    """
    Call Nager.Date external holiday API.
    Sends GET request — returns JSON holiday data.
    No API key required.
    """
    url = f"{NAGER_API_URL}/{year}/{country}"
    try:
        response = ext_requests.get(
            url,
            timeout=8,
            headers={
                "Accept": "application/json",
                "User-Agent": "AttendancePro/1.0"
            }
        )
        if response.status_code == 200:
            data = response.json()
            # Filter by month if provided
            if month:
                data = [h for h in data if h["date"].split("-")[1] == str(month).zfill(2)]
            return {"success": True, "data": data, "status": 200, "url": url}
        else:
            return {"success": False, "error": f"API returned status {response.status_code}", "status": response.status_code, "url": url}
    except ext_requests.exceptions.ConnectionError:
        return {"success": False, "error": "No internet connection", "status": 0, "url": url}
    except ext_requests.exceptions.Timeout:
        return {"success": False, "error": "API request timed out", "status": 0, "url": url}
    except Exception as e:
        return {"success": False, "error": str(e), "status": 0, "url": url}


@app.route("/holidays", methods=["GET", "POST"])
@login_required
def holidays():
    today   = date.today()
    country = request.args.get("country", "IN")
    year    = request.args.get("year",    str(today.year))
    month   = request.args.get("month",   "")
    api_result    = None
    holidays_data = []
    error_msg     = None

    countries = [
        ("IN","India"), ("US","United States"), ("GB","United Kingdom"),
        ("AU","Australia"), ("CA","Canada"), ("SG","Singapore"),
        ("AE","UAE"), ("JP","Japan"), ("DE","Germany"), ("FR","France"),
    ]

    if request.args.get("fetch"):
        result = fetch_holidays_from_api(
            country=country,
            year=int(year),
            month=int(month) if month else None,
        )
        api_result = result
        if result["success"]:
            holidays_data = result["data"]
        else:
            error_msg = result["error"]

    # Check if today is a holiday
    today_holiday = None
    if holidays_data:
        for h in holidays_data:
            if h["date"] == str(today):
                today_holiday = h
                break

    # Upcoming holidays
    upcoming = []
    for h in holidays_data:
        try:
            hdate = date.fromisoformat(h["date"])
            if hdate >= today:
                upcoming.append({**h, "date_obj": hdate})
        except:
            pass
    upcoming = upcoming[:5]

    return render_template("holidays.html",
        holidays=holidays_data,
        api_result=api_result,
        error_msg=error_msg,
        country=country,
        year=year,
        month=month,
        countries=countries,
        today=today,
        today_holiday=today_holiday,
        upcoming=upcoming,
        api_url=NAGER_API_URL,
    )


@app.route("/api/external/holidays")
@login_required
def api_external_holidays():
    """
    REST API endpoint — calls Nager.Date externally and returns JSON.
    GET /api/external/holidays?country=IN&year=2026&month=3
    """
    country = request.args.get("country", "IN")
    year    = request.args.get("year",    str(date.today().year))
    month   = request.args.get("month",   None)

    result = fetch_holidays_from_api(country, int(year), int(month) if month else None)

    return jsonify({
        "external_api":   "Nager.Date — date.nager.at",
        "endpoint":       f"{NAGER_API_URL}/{year}/{country}",
        "request_params": {"country": country, "year": year, "month": month},
        "success":        result["success"],
        "total":          len(result.get("data", [])),
        "data":           result.get("data", []),
        "error":          result.get("error"),
    })

if __name__ == "__main__":
    app.run(debug=True)
