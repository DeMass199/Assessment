from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, date, timedelta
import os
import logging
import calendar

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Update the db_path to be a constant at the top level
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'todo.db')

def add_user_to_db(username, password):
    """Adds a new user to the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if username exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return False
        
        # Hash password and insert user
        hashed_password = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",  # Removed extra ? from VALUES
            (username, hashed_password)  # Matches the two ? placeholders
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False

# Database initialization function
def init_db():
    """Initialize the database with proper schema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create fresh tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                task TEXT NOT NULL,
                due_date TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0,
                category TEXT DEFAULT 'General',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        conn.commit()
        logger.info("Database initialized successfully")
        return True
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
        return False
    finally:
        conn.close()

def migrate_db():
    """Add new columns to existing tables"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if category column exists
        cursor.execute("PRAGMA table_info(todos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add category column if it doesn't exist
        if 'category' not in columns:
            cursor.execute("ALTER TABLE todos ADD COLUMN category TEXT DEFAULT 'General'")
            conn.commit()
            logger.info("Added category column to todos table")
        
        conn.close()
        return True
    except sqlite3.Error as e:
        logger.error(f"Database migration error: {e}")
        return False

# Initialize and migrate the database
init_db()
migrate_db()

# Update validate_user function
def validate_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            return user
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return None


@app.route("/")
def home():
    stats = {
        'total_users': 0,
        'total_tasks': 0
    }
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM todos")
        stats['total_tasks'] = cursor.fetchone()[0]
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Error fetching stats: {e}")
    
    return render_template("index.html", stats=stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("Please provide both username and password", "error")
            return redirect(url_for("login"))
            
        user = validate_user(username, password)
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        
        flash("Invalid username or password!", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for("signup"))
        
        # Try to add user to database
        if add_user_to_db(username, password):
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Username already exists or an error occurred.", "error")
            return redirect(url_for("signup"))

    return render_template("signup.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if 'user_id' not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))
        
    if request.method == "POST":
        task = request.form.get("todo_task")
        due_date_str = request.form.get("due_date")
        category = request.form.get("category")  # Get category from form
        
        if task and due_date_str and category:
            try:
                # Parse only the date
                due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
                due_date_iso = due_date.date().isoformat()
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO todos (user_id, task, due_date, category) VALUES (?, ?, ?, ?)",
                    (session['user_id'], task, due_date_iso, category)
                )
                conn.commit()
                conn.close()
                flash("Task added successfully!", "success")
            except ValueError:
                flash("Invalid date format.", "error")
                return redirect(url_for("dashboard"))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, due_date, category FROM todos WHERE user_id = ?", (session['user_id'],))
    todos = cursor.fetchall()
    conn.close()
    
    # Format todos for template
    todo_list = []
    for todo in todos:
        due_date = datetime.fromisoformat(todo[2])
        time_left = due_date - datetime.now()
        
        if time_left.total_seconds() < 0:
            color = "red"  # Overdue
        elif time_left <= timedelta(days=7):
            color = "yellow"  # Due soon
        else:
            color = "on-time"
            
        todo_list.append({
            "id": todo[0],
            "task": todo[1],
            "due_date": due_date.strftime("%Y-%m-%d"),
            "category": todo[3],
            "color": color
        })
        
    return render_template("dashboard.html", todo_list=todo_list)


@app.route("/delete/dashboard/<int:task_id>")
def delete_task(task_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ? AND user_id = ?", (task_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out!", "success")
    return redirect(url_for("login"))


@app.route("/calendar")
def calendar_view():
    if 'user_id' not in session:
        flash("Please login first!", "error")
        return redirect(url_for("login"))

    # Get current year and month from query parameters or use current date
    year = int(request.args.get('year', datetime.now().year))
    month = int(request.args.get('month', datetime.now().month))

    # Calculate previous and next month/year
    first_day = date(year, month, 1)
    prev_month = (first_day - timedelta(days=1)).replace(day=1)
    next_month = (first_day + timedelta(days=32)).replace(day=1)

    # Get calendar data
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    # Get tasks for the current month
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT task, due_date FROM todos 
        WHERE user_id = ? 
        AND strftime('%Y-%m', due_date) = strftime('%Y-%m', ?)
    """, (session['user_id'], f"{year}-{month:02d}-01"))
    tasks = cursor.fetchall()
    conn.close()

    # Organize tasks by date
    task_dict = {}
    for task in tasks:
        task_date = datetime.strptime(task[1], "%Y-%m-%d").date()
        if task_date not in task_dict:
            task_dict[task_date] = []
        task_dict[task_date].append({
            "task": task[0],
            "color": "red" if task_date < date.today() else "yellow" if task_date <= date.today() + timedelta(days=7) else "on-time"
        })

    # Build calendar data
    calendar_data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append({"day": "", "tasks": []})
            else:
                current_date = date(year, month, day)
                week_data.append({
                    "day": day,
                    "today": current_date == date.today(),
                    "tasks": task_dict.get(current_date, [])
                })
        calendar_data.append(week_data)

    return render_template("calendar.html",
                         calendar_data=calendar_data,
                         month_name=month_name,
                         year=year,
                         prev_month=prev_month.month,
                         prev_year=prev_month.year,
                         next_month=next_month.month,
                         next_year=next_month.year,
                         active_page='calendar')


if __name__ == "__main__":
    app.run(debug=True)