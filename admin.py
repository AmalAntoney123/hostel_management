from flask import Blueprint, redirect, render_template, request, jsonify, session, url_for
from werkzeug.security import generate_password_hash
from config import users
from utils import login_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route("/admin_dashboard")
@login_required
def admin_dashboard():
    if session["user"]["role"] != "admin":
        return redirect(url_for("index"))
    return render_template("admin_dashboard.html")

@admin_bp.route("/add_user", methods=["POST"])
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

    password = f"{username}@{phone[-4:]}"
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

    return {
        "success": True,
        "message": f"{role.capitalize()} added successfully",
        "username": username,
        "password": password
    }