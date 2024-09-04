from flask import Blueprint, render_template, session, redirect, url_for
from utils import login_required

student_bp = Blueprint('student', __name__)

@student_bp.route("/student_dashboard")
@login_required
def student_dashboard():
    if session["user"]["role"] != "student":
        return redirect(url_for("index"))
    return render_template("student_dashboard.html")