from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, date, time

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flash messages

def add_user_to_db(username, password):
    """Adds a new user to the database if the username doesn't already exist."""
    try:
        conn = sqlite3.connect("todo.db")
        cursor = conn.cursor()
        
        # Check if the username already exists
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Username already exists. Please choose a different username.")
            return redirect(url_for('register'))
        
        # Hash the password and insert the new user
        hashed_password = generate_password_hash(password, method='sha256')
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        flash("User registered successfully!")
        return redirect(url_for('login'))
    except sqlite3.Error as e:
        flash(f"An error occurred: {e}")
        return redirect(url_for('register'))
    finally:
        conn.close()

# Database initialization function
def init_db():
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# Initialize the database
init_db()


# Helper function to validate user credentials
def validate_user(username, password):
    conn = sqlite3.connect("todo.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user:
        stored_password_hash = user[2]  # Assuming the password hash is in the 3rd column (index 2)
        return check_password_hash(stored_password_hash, password)
    return False


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Username and password are required!", "error")
            return redirect(url_for("signup"))

        # Attempt to add the user to the database
        if add_user_to_db(username, password):
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))  # Redirect to login page
        else:
            flash("Username is already taken. Please choose another one.", "error")

    return render_template("signup.html")





# Sample in-memory storage for demonstration
todo_list = []

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    global todo_list
    if request.method == "POST":
        task = request.form.get("todo_task")
        due_date = request.form.get("due_date")
        if task and due_date:
            # Add task with an ID and due date
            todo_list.append({
                "id": len(todo_list) + 1,
                "task": task,
                "due_date": due_date,
                "done": False,
                "color": ""  # Optional, can calculate color here or in template
            })
        return render_template("dashboard.html", todo_list=todo_list)
    
    # Set the color for each task based on due date
    for item in todo_list:
        if item.get("due_date"):
            today = datetime.date.today()
            due_date = datetime.datetime.strptime(item["due_date"], "%Y-%m-%d").date()
            days_left = (due_date - today).days
            if days_left < 0:
                item["color"] = "overdue"
            elif days_left <= 7:
                item["color"] = "due-soon"
            else:
                item["color"] = "on-time"

    return render_template("dashboard.html", todo_list=todo_list)


@app.route("/delete/dashboard/<int:task_id>")
def delete_task(task_id):
    global todo_list
    # Remove the task with the matching ID
    todo_list = [item for item in todo_list if item["id"] != task_id]
    return render_template("dashboard.html", todo_list=todo_list)


if __name__ == "__main__":
    app.run(debug=True)