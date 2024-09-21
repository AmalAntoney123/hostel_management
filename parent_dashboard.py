from flask import Blueprint, jsonify, session
from bson import ObjectId
from config import db, users
from utils import login_required
from datetime import datetime, timedelta
import random
import traceback

parent_dashboard_bp = Blueprint("parent_dashboard", __name__)

@parent_dashboard_bp.route("/parent/get_recent_activities")
@login_required
def get_recent_activities():
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
        if not parent or "associated_student" not in parent:
            return jsonify({"success": False, "message": "No associated student found"}), 400

        student_id = parent["associated_student"]

        # Fetch recent activities from various collections
        activities = []

        # Fetch recent attendance
        recent_attendance = list(db.attendance.find({"student_id": str(student_id)}).sort("date", -1).limit(3))
        for attendance in recent_attendance:
            timestamp = attendance.get('date')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            activities.append({
                "title": "Attendance",
                "description": f"Marked on {timestamp.strftime('%Y-%m-%d')}",
                "timestamp": timestamp
            })

        # Fetch recent fee payments
        recent_payments = list(db.payments.find({"student_id": str(student_id)}).sort("payment_date", -1).limit(3))
        for payment in recent_payments:
            timestamp = payment.get('payment_date')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            activities.append({
                "title": "Fee Payment",
                "description": f"Paid ₹{payment.get('amount', 'Unknown')} for {payment.get('description', 'Unknown')}",
                "timestamp": timestamp
            })

        # Fetch recent outing requests
        recent_outings = list(db.outing_requests.find({"student_id": str(student_id)}).sort("submitted_at", -1).limit(3))
        for outing in recent_outings:
            timestamp = outing.get('submitted_at')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            activities.append({
                "title": "Outing Request",
                "description": f"Requested outing for {outing.get('reason', 'Unknown reason')}",
                "timestamp": timestamp
            })

        # Sort activities by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)

        # Convert datetime objects to ISO format strings for JSON serialization
        for activity in activities:
            activity['timestamp'] = activity['timestamp'].isoformat()

        return jsonify({"success": True, "activities": activities[:5]})  # Return top 5 activities

    except Exception as e:
        print(f"Error fetching recent activities: {str(e)}")
        print(traceback.format_exc())  # This will print the full stack trace
        return jsonify({"success": False, "message": "An error occurred while fetching recent activities"}), 500

# Add more routes related to the parent dashboard here if needed
