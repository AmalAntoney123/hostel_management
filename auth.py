from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from config import users
from utils import login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = users.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["user"] = {"username": user["username"], "role": user["role"]}
            flash(f"Welcome, {user['username']}!", "success")
            return redirect(url_for(f'{user["role"]}_dashboard'))
        else:
            flash("Invalid username or password", "error")
    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))