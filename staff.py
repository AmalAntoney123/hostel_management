from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from utils import login_required
from datetime import datetime
from config import db  # Add this import
from bson import ObjectId

staff_bp = Blueprint('staff', __name__)

@staff_bp.route("/staff_dashboard")
@login_required
def staff_dashboard():
    if session["user"]["role"] != "staff":
        return redirect(url_for("index"))
    return render_template("staff_dashboard.html")

@staff_bp.route("/staff/submit_complaint", methods=["POST"])
@login_required
def staff_submit_complaint():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        subject = data.get('subject')
        description = data.get('description')

        if not all([subject, description]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        complaint = {
            "user_id": session["user"]["username"],
            "user_role": "staff",
            "subject": subject,
            "description": description,
            "status": "pending",
            "timestamp": datetime.utcnow(),
            "admin_comment": ""
        }

        result = db.complaints.insert_one(complaint)

        if result.inserted_id:
            return jsonify({"success": True, "message": "Complaint submitted successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to submit complaint"}), 500

    except Exception as e:
        print(f"Error submitting complaint: {str(e)}")  # Log the error
        return jsonify({"success": False, "message": "An error occurred while submitting the complaint"}), 500

@staff_bp.route("/staff/get_user_complaints", methods=["GET"])
@login_required
def staff_get_user_complaints():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    complaints = list(db.complaints.find({"user_id": session["user"]["username"]}))
    for complaint in complaints:
        complaint['_id'] = str(complaint['_id'])
        complaint['timestamp'] = complaint['timestamp'].isoformat()

    return jsonify({"success": True, "complaints": complaints})

@staff_bp.route("/staff/submit_inventory_request", methods=["POST"])
@login_required
def staff_submit_inventory_request():
    print(f"Current user role: {session.get('user', {}).get('role')}")  # Debug print
    if session.get("user", {}).get("role") != "staff":
        print("Unauthorized access attempt to submit_inventory_request")  # Debug print
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        item_name = data.get('itemName')
        quantity = data.get('quantity')
        reason = data.get('reason')

        if not all([item_name, quantity, reason]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        inventory_request = {
            "staff_id": session["user"]["username"],
            "item_name": item_name,
            "quantity": int(quantity),
            "reason": reason,
            "status": "pending",
            "timestamp": datetime.utcnow(),
            "admin_comment": ""
        }

        result = db.inventory_requests.insert_one(inventory_request)

        if result.inserted_id:
            return jsonify({"success": True, "message": "Inventory request submitted successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to submit inventory request"}), 500

    except Exception as e:
        print(f"Error submitting inventory request: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while submitting the inventory request"}), 500

@staff_bp.route("/staff/get_inventory_requests", methods=["GET"])
@login_required
def staff_get_inventory_requests():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    requests = list(db.inventory_requests.find({"staff_id": session["user"]["username"]}).sort("timestamp", -1))
    for request in requests:
        request['_id'] = str(request['_id'])
        request['timestamp'] = request['timestamp'].isoformat()

    return jsonify({"success": True, "requests": requests})

@staff_bp.route("/staff/get_staff_schedule", methods=["GET"])
@login_required
def get_staff_schedule():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    staff_id = str(session["user"]["_id"])
    schedules = list(db.schedules.find({"staff_id": staff_id}))
    for schedule in schedules:
        schedule["_id"] = str(schedule["_id"])
        schedule["start_date"] = schedule["start_date"].strftime("%Y-%m-%d")
        schedule["end_date"] = schedule["end_date"].strftime("%Y-%m-%d")

    return jsonify({"success": True, "schedules": schedules})