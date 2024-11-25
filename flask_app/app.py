from flask import Flask, request, render_template, redirect, url_for
from werkzeug.security import check_password_hash
import sqlite3

app = Flask(__name__)


def validate_user(username, password):
    conn = sqlite3.connect('todo.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user:
        stored_password_hash = user[2]  # Assuming the password is in the 3rd column (index 2)
        return check_password_hash(stored_password_hash, password)
    return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

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
