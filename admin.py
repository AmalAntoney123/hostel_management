from flask import Blueprint, redirect, render_template, request, jsonify, session, url_for
from werkzeug.security import generate_password_hash
from config import users
from utils import login_required
import pandas as pd
import io

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
        "password": hashed_password,
        "is_active": True  # Add this line
    }

    users.insert_one(new_user)

    return {
        "success": True,
        "message": f"{role.capitalize()} added successfully",
        "username": username,
        "password": password
    }

@admin_bp.route("/get_users/<role>", methods=["GET"])
@login_required
def get_users(role):
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    if role not in ["student", "staff"]:
        return {"success": False, "message": "Invalid role"}, 400

    # Use inclusion projection instead of mixing inclusion and exclusion
    user_list = list(users.find(
        {"role": role}, 
        {"_id": 0, "username": 1, "full_name": 1, "email": 1, "phone": 1, "is_active": 1}
    ))
    return jsonify({"success": True, "users": user_list})

@admin_bp.route("/bulk_upload_users", methods=["POST"])
@login_required
def bulk_upload_users():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    if 'excelFile' not in request.files:
        return {"success": False, "message": "No file part"}, 400

    file = request.files['excelFile']
    user_type = request.form.get('userType')

    if file.filename == '':
        return {"success": False, "message": "No selected file"}, 400

    if user_type not in ['student', 'staff']:
        return {"success": False, "message": "Invalid user type"}, 400

    try:
        df = pd.read_excel(file) if file.filename.endswith(('.xls', '.xlsx')) else pd.read_csv(file)
        required_columns = ['username', 'full_name', 'email', 'phone']
        
        if not all(col in df.columns for col in required_columns):
            return {"success": False, "message": "Missing required columns"}, 400

        success_count = 0
        error_count = 0

        for _, row in df.iterrows():
            username = row['username']
            full_name = row['full_name']
            email = row['email']
            phone = str(row['phone'])

            existing_user = users.find_one({"username": username})
            if existing_user:
                error_count += 1
                continue

            password = f"{username}@{phone[-4:]}"
            hashed_password = generate_password_hash(password)

            new_user = {
                "username": username,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "role": user_type,
                "password": hashed_password,
                "is_active": True  # Add this line
            }

            users.insert_one(new_user)
            success_count += 1

        return {
            "success": True,
            "message": f"Uploaded {success_count} users successfully. {error_count} users failed."
        }

    except Exception as e:
        return {"success": False, "message": f"Error processing file: {str(e)}"}, 500

@admin_bp.route("/toggle_user_status", methods=["POST"])
@login_required
def toggle_user_status():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    username = data.get("username")
    role = data.get("role")

    if not username or role not in ["student", "staff"]:
        return {"success": False, "message": "Invalid request"}, 400

    user = users.find_one({"username": username, "role": role})
    if not user:
        return {"success": False, "message": "User not found"}, 404

    new_status = not user.get("is_active", True)
    users.update_one({"username": username}, {"$set": {"is_active": new_status}})

    return {"success": True, "message": f"User status updated to {'active' if new_status else 'disabled'}"}

@admin_bp.route("/reset_user_password", methods=["POST"])
@login_required
def reset_user_password():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    username = data.get("username")
    role = data.get("role")

    if not username or role not in ["student", "staff"]:
        return {"success": False, "message": "Invalid request"}, 400

    user = users.find_one({"username": username, "role": role})
    if not user:
        return {"success": False, "message": "User not found"}, 404

    new_password = f"{username}@{user['phone'][-4:]}"
    hashed_password = generate_password_hash(new_password)

    users.update_one({"username": username}, {"$set": {"password": hashed_password}})

    return {"success": True, "message": "Password reset successfully", "password": new_password}