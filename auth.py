from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from config import users
from utils import login_required
from google_auth import flow, verify_google_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["user"] = {
                "username": user["username"],
                "role": user["role"],
                "_id": str(user["_id"])  # Add this line
            }
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

