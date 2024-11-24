from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from werkzeug.security import check_password_hash

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

@app.route('/dashboard', methods=['POST'])
def dashboard():
    username = request.form['username']
    password = request.form['password']
    print(f"Attempting login for: {username} with password: {password}")
    
    if validate_user(username, password):
        return "<h1>Welcome to your Dashboard</h1>"
    else:
        return "<h1>Invalid Username or Password</h1>"
    
if __name__ == '__main__':
    app.run(debug=True)
