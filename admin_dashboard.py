from flask import Blueprint, jsonify, session, request
from bson import ObjectId
from config import db, users
from utils import login_required
from datetime import datetime, timedelta
import traceback

admin_dashboard_bp = Blueprint("admin_dashboard", __name__)

@admin_dashboard_bp.route("/admin/get_dashboard_stats")
@login_required
def get_dashboard_stats():
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Get total number of students
        total_students = users.count_documents({"role": "student"})

        # Get room occupancy
        total_rooms = db.rooms.count_documents({})
        occupied_rooms = db.rooms.count_documents({"occupied": True})
        occupancy_rate = (occupied_rooms / total_rooms) * 100 if total_rooms > 0 else 0

        # Get pending fees
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        pending_fees = db.payments.aggregate([
            {"$match": {"status": "pending", "due_date": {"$gte": current_month}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ])
        pending_fees_amount = next(pending_fees, {}).get("total", 0)

        # Get open complaints
        open_complaints = db.complaints.count_documents({"status": "pending"})

        return jsonify({
            "success": True,
            "stats": {
                "total_students": total_students,
                "occupancy_rate": round(occupancy_rate, 2),
                "pending_fees": pending_fees_amount,
                "open_complaints": open_complaints
            }
        })

    except Exception as e:
        print(f"Error fetching dashboard stats: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": "An error occurred while fetching dashboard stats"}), 500

@admin_dashboard_bp.route("/admin/get_recent_activities")
@login_required
def get_recent_activities():
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        activities = []

        # Get recent registrations
        recent_registrations = list(users.find({"role": "student"}).sort("join_date", -1).limit(5))
        for reg in recent_registrations:
            activities.append({
                "type": "registration",
                "description": f"New student registered: {reg['full_name']}",
                "timestamp": reg['join_date']
            })

        # Get recent complaints
        recent_complaints = list(db.complaints.find().sort("timestamp", -1).limit(5))
        for complaint in recent_complaints:
            activities.append({
                "type": "complaint",
                "description": f"New complaint: {complaint['subject']}",
                "timestamp": complaint['timestamp']
            })

        # Get recent payments
        recent_payments = list(db.payments.find().sort("payment_date", -1).limit(5))
        for payment in recent_payments:
            activities.append({
                "type": "payment",
                "description": f"Payment received: ₹{payment['amount']} for {payment['description']}",
                "timestamp": payment['payment_date']
            })

        # Sort all activities by timestamp
        activities.sort(key=lambda x: x['timestamp'], reverse=True)

        # Convert datetime objects to ISO format strings for JSON serialization
        for activity in activities:
            activity['timestamp'] = activity['timestamp'].isoformat()

        return jsonify({"success": True, "activities": activities[:10]})  # Return top 10 activities

    except Exception as e:
        print(f"Error fetching recent activities: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": "An error occurred while fetching recent activities"}), 500

@admin_dashboard_bp.route("/admin/get_occupancy_chart_data")
@login_required
def get_occupancy_chart_data():
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        total_rooms = db.rooms.count_documents({})
        occupied_rooms = db.rooms.count_documents({"occupied": True})
        vacant_rooms = total_rooms - occupied_rooms

        return jsonify({
            "success": True,
            "data": {
                "labels": ["Occupied", "Vacant"],
                "datasets": [{
                    "data": [occupied_rooms, vacant_rooms],
                    "backgroundColor": ["#28a745", "#dc3545"]
                }]
            }
        })

    except Exception as e:
        print(f"Error fetching occupancy chart data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": "An error occurred while fetching occupancy chart data"}), 500

@admin_dashboard_bp.route("/admin/get_fee_collection_chart_data")
@login_required
def get_fee_collection_chart_data():
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)  # Last 6 months

        pipeline = [
            {"$match": {"payment_date": {"$gte": start_date, "$lte": end_date}}},
            {"$group": {
                "_id": {"$dateToString": {"format": "%Y-%m", "date": "$payment_date"}},
                "total": {"$sum": "$amount"}
            }},
            {"$sort": {"_id": 1}}
        ]

        result = list(db.payments.aggregate(pipeline))

        labels = []
        data = []
        for item in result:
            labels.append(item["_id"])
            data.append(item["total"])

        return jsonify({
            "success": True,
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": "Fee Collection",
                    "data": data,
                    "backgroundColor": "#007bff"
                }]
            }
        })

    except Exception as e:
        print(f"Error fetching fee collection chart data: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": "An error occurred while fetching fee collection chart data"}), 500
