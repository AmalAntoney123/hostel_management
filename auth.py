from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from config import users
from utils import login_required
from google_auth import flow, verify_google_token
from bson import ObjectId
import re

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.find_one({"username": username})
        
        if not user:
            # Check if the username is a parent name
            parent = users.find_one({"full_name": username, "role": "parent"})
            if parent:
                user = parent
            else:
                flash("Invalid username or password", "error")
                return render_template("login.html")

        if user and check_password_hash(user["password"], password):
            session["user"] = {
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "_id": str(user["_id"])
            }
            if user["role"] == "parent":
                session["user"]["associated_student"] = str(user["associated_student"])
                flash(f"Welcome, {user['full_name']}!", "success")
                return redirect(url_for("parent.parent_dashboard"))
            else:
                flash(f"Welcome, {user['username']}!", "success")
                return redirect(url_for(f'{user["role"]}.{user["role"]}_dashboard'))
        else:
            flash("Invalid username or password", "error")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))

@auth_bp.route("/google_login")
def google_login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@auth_bp.route("/callback")
def callback():
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        token = credentials.id_token
        user_info = verify_google_token(token)

        if user_info:
            email = user_info['email']
            user = users.find_one({"email": email})

            if user:
                session["user"] = {
                    "username": user["username"],
                    "role": user["role"],
                    "_id": str(user["_id"])  # Add this line
                }
                users.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"google_id": user_info['sub']}}
                )
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for(f"{user['role']}.{user['role']}_dashboard"))
            else:
                flash("No account found with this email. Please contact the administrator or use regular login.", "error")
                return redirect(url_for("auth.login"))
        else:
            flash("Google authentication failed: Unable to verify token", "error")
            return redirect(url_for("auth.login"))
    except Exception as e:
        flash(f"Google authentication failed: {str(e)}", "error")
        return redirect(url_for("auth.login"))


@auth_bp.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    user_id = ObjectId(session["user"]["_id"])
    user = users.find_one({"_id": user_id})

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    full_name = request.form.get("full_name")
    email = request.form.get("email")
    phone = request.form.get("phone")

    # Validate full name
    if not full_name or len(full_name) < 2:
        return jsonify({"success": False, "message": "Full name must be at least 2 characters long"}), 400

    # Validate email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"success": False, "message": "Invalid email address"}), 400

    # Check if email is already in use by another user
    existing_user = users.find_one({"email": email, "_id": {"$ne": user_id}})
    if existing_user:
        return jsonify({"success": False, "message": "Email address is already in use"}), 400

    # Validate phone number
    if not re.match(r"^\+?1?\d{9,15}$", phone):
        return jsonify({"success": False, "message": "Invalid phone number"}), 400

    # Update user data
    update_data = {
        "full_name": full_name,
        "email": email,
        "phone": phone
    }

    users.update_one({"_id": user_id}, {"$set": update_data})

    return jsonify({"success": True, "message": "Profile updated successfully"})

@auth_bp.route("/change_password", methods=["POST"])
@login_required
def change_password():
    user_id = ObjectId(session["user"]["_id"])
    current_password = request.form.get("current_password")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    user = users.find_one({"_id": user_id})

    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404

    if not check_password_hash(user["password"], current_password):
        return jsonify({"success": False, "message": "Current password is incorrect"}), 400
    elif new_password != confirm_password:
        return jsonify({"success": False, "message": "New passwords do not match"}), 400
    elif len(new_password) < 8:
        return jsonify({"success": False, "message": "New password must be at least 8 characters long"}), 400
    else:
        hashed_password = generate_password_hash(new_password)
        users.update_one({"_id": user_id}, {"$set": {"password": hashed_password}})
        return jsonify({"success": True, "message": "Password changed successfully"})