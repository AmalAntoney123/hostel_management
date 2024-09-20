from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from bson import ObjectId
from config import db, users
from utils import login_required

parent_bp = Blueprint("parent", __name__)

@parent_bp.route("/parent_dashboard")
@login_required
def parent_dashboard():
    if session["user"]["role"] != "parent":
        return redirect(url_for("index"))
    
    # Use "_id" instead of "id"
    parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
    
    # Check if the parent exists and has an associated student
    if parent and "associated_student" in parent:
        student = users.find_one({"_id": ObjectId(parent["associated_student"])})
    else:
        student = None

    return render_template("parent_dashboard.html", parent=parent, student=student)

