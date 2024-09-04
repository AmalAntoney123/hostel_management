from flask import Blueprint, render_template, session, redirect, url_for
from utils import login_required

staff_bp = Blueprint('staff', __name__)

@staff_bp.route("/staff_dashboard")
@login_required
def staff_dashboard():
    if session["user"]["role"] != "staff":
        return redirect(url_for("index"))
    return render_template("staff_dashboard.html")