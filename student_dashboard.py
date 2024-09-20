from flask import Blueprint, jsonify, session, current_app
from bson import ObjectId
from config import db, users
from datetime import datetime, timedelta
import traceback

student_dashboard_bp = Blueprint("student_dashboard", __name__)

@student_dashboard_bp.route("/student/dashboard_data")
def get_dashboard_data():
    try:
        current_app.logger.info("Starting get_dashboard_data")
        
        if "user" not in session:
            current_app.logger.error("User not in session")
            return jsonify({"error": "User not authenticated"}), 401

        student_id = ObjectId(session["user"]["_id"])
        current_app.logger.info(f"Student ID: {student_id}")

        student = users.find_one({"_id": student_id})
        current_app.logger.info(f"Student found: {bool(student)}")

        if not student:
            return jsonify({"error": "Student not found"}), 404

        # Fetch room information
        current_app.logger.info("Fetching room assignment")
        room_assignment = db.room_assignments.find_one({"student_id": str(student_id)})
        current_app.logger.info(f"Room assignment found: {bool(room_assignment)}")

        room_info = {
            "block": room_assignment["block_name"] if room_assignment else "Not Assigned",
            "room_number": room_assignment["room_number"] if room_assignment else "Not Assigned"
        }

        # Fetch upcoming payments
        current_date = datetime.now()
        upcoming_payments = list(db.payments.find({
            "student_id": str(student_id),
            "due_date": {"$gte": current_date}
        }).sort("due_date", 1).limit(3))

        # Convert ObjectId to string for each payment
        for payment in upcoming_payments:
            payment["_id"] = str(payment["_id"])
            payment["due_date"] = payment["due_date"].isoformat()  # Add this line

        # Fetch recent complaints
        recent_complaints = list(db.complaints.find({
            "user_id": student["username"]
        }).sort("timestamp", -1).limit(3))

        # Convert ObjectId to string for each complaint
        for complaint in recent_complaints:
            complaint["_id"] = str(complaint["_id"])

        # Fetch recent notices
        recent_notices = list(db.notices.find({
            "$or": [{"target": "all"}, {"target": "students"}]
        }).sort("posted_date", -1).limit(3))

        # Convert ObjectId to string for each notice
        for notice in recent_notices:
            notice["_id"] = str(notice["_id"])

        # Fetch attendance summary
        thirty_days_ago = current_date - timedelta(days=30)
        attendance_records = db.attendance.find({
            "student_id": str(student_id),
            "date": {"$gte": thirty_days_ago.date().isoformat()}
        })
        attendance_count = len(list(attendance_records))
        attendance_percentage = (attendance_count / 30) * 100

        dashboard_data = {
            "room_info": room_info,
            "upcoming_payments": upcoming_payments,
            "recent_complaints": recent_complaints,
            "recent_notices": recent_notices,
            "attendance_summary": {
                "percentage": round(attendance_percentage, 2),
                "days_present": attendance_count
            }
        }

        return jsonify(dashboard_data)

    except Exception as e:
        current_app.logger.error(f"Error in get_dashboard_data: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "An internal error occurred"}), 500