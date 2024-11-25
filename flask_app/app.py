from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3


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
            return False  # Username is already taken

        # Hash the password before storing it
        password_hash = generate_password_hash(password)

        # Insert the new user into the database
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password_hash))
        conn.commit()
        return True  # User added successfully

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False

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
        # Get the input from the form
        task = request.form.get("todo_task")
        if task:  # Ensure the input isn't empty
            # Add the task to the list (or database in a real app)
            todo_list.append({"id": len(todo_list) + 1, "task": task, "done": False})
        return redirect(url_for("dashboard"))
    return render_template("dashboard.html", todo_list=todo_list)


@app.route("/delete/dashboard/<int:task_id>")
def delete_task(task_id):
    global todo_list
    # Remove the task with the matching ID
    todo_list = [item for item in todo_list if item["id"] != task_id]
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)

