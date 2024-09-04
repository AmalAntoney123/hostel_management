from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from functools import wraps
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

import random
import string
import re

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.secret_key = os.getenv("SECRET_KEY")

# MongoDB Atlas connection
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
users = db.users
rooms = db.rooms
fees = db.fees
students = db["students"]


# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["user"] = {"username": user["username"], "role": user["role"]}
            return redirect(url_for(f'{user["role"]}_dashboard'))
        else:
            flash("Invalid username or password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


@app.route("/student_dashboard")
@login_required
def student_dashboard():
    if session["user"]["role"] != "student":
        return redirect(url_for("index"))
    return render_template("student_dashboard.html")


@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
    if session["user"]["role"] != "admin":
        return redirect(url_for("index"))
    return render_template("admin_dashboard.html")


@app.route("/staff_dashboard")
@login_required
def staff_dashboard():
    if session["user"]["role"] != "staff":
        return redirect(url_for("index"))
    return render_template("staff_dashboard.html")


@app.route("/add_user", methods=["POST"])
@login_required
def add_user():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    username = data.get("username")
    full_name = data.get("full_name")
    email = data.get("email")
    phone = data.get("phone")
    role = data.get("role")

    if not all([username, full_name, email, phone, role]):
        return {"success": False, "message": "Missing required fields"}, 400

    existing_user = users.find_one({"username": username})
    if existing_user:
        return {"success": False, "message": "Username already exists"}, 400

    # Generate password
    password = f"{username}@{phone[-4:]}"

    # Hash the password
    hashed_password = generate_password_hash(password)

    new_user = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "role": role,
        "password": hashed_password,
    }

    users.insert_one(new_user)

    return {
        "success": True,
        "message": f"{role.capitalize()} added successfully",
        "username": username,
        "password": password,
    }


@app.route("/add_multiple_users", methods=["POST"])
@login_required
def add_multiple_users():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    role = data.get("role")
    users_data = data.get("users")

    if not role or not users_data:
        return {"success": False, "message": "Missing required fields"}, 400

    added_users = []

    for user_data in users_data:
        username = user_data.get("username")
        full_name = user_data.get("full_name")
        email = user_data.get("email")
        phone = user_data.get("phone")

        if not all([username, full_name, email, phone]):
            continue

        existing_user = users.find_one({"username": username})
        if existing_user:
            continue

        # Generate password
        password = f"{username}@{phone[-4:]}"

        # Hash the password
        hashed_password = generate_password_hash(password)

        new_user = {
            "username": username,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "role": role,
            "password": hashed_password
        }

        users.insert_one(new_user)
        added_users.append({"username": username, "password": password})

    if added_users:
        return {
            "success": True,
            "message": f"{len(added_users)} {role}(s) added successfully",
            "users": added_users
        }
    else:
        return {"success": False, "message": "No users were added"}, 400


def generate_unique_username(full_name):
    # Remove spaces and convert to lowercase
    base_username = re.sub(r'\s+', '', full_name).lower()
    
    # Check if the base username exists
    existing_user = users.find_one({"username": base_username})
    if not existing_user:
        return base_username

    # If it exists, add a number at the end
    counter = 1
    while True:
        new_username = f"{base_username}{counter}"
        existing_user = users.find_one({"username": new_username})
        if not existing_user:
            return new_username
        counter += 1


# Add more routes for specific functionalities

if __name__ == "__main__":
    app.run(debug=True)
