from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
import numpy as np
from face_recognition_utils import recognize_face
from utils import login_required, send_email, can_send_notification
from datetime import datetime
from config import db, users
from bson import ObjectId

staff_bp = Blueprint('staff', __name__)

@staff_bp.route("/staff_dashboard")
@login_required
def staff_dashboard():
    if session["user"]["role"] != "staff":
        return redirect(url_for("index"))
    user_id = ObjectId(session["user"]["_id"])
    user = users.find_one({"_id": user_id})
    return render_template("staff_dashboard.html",  user=user)


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

@staff_bp.route("/staff/get_notices", methods=["GET"])
@login_required
def get_staff_notices():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    notices = list(db.notices.find({"$or": [{"target": "all"}, {"target": "staff"}]}).sort("posted_date", -1))
    for notice in notices:
        notice["_id"] = str(notice["_id"])
        notice["posted_date"] = notice["posted_date"].isoformat()

    return jsonify({"success": True, "notices": notices})

@staff_bp.route("/staff/mark_attendance", methods=["POST"])
@login_required
def mark_attendance():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        image_data = request.json.get("image_data")

        # Get all student face encodings
        students = list(users.find({"role": "student", "face_encoding": {"$exists": True}}))
        known_face_encodings = [np.array(student["face_encoding"]) for student in students]
        student_ids = [str(student["_id"]) for student in students]

        # Recognize the face
        recognized_index = recognize_face(image_data, known_face_encodings)

        if recognized_index is None:
            return jsonify({"success": False, "message": "No matching student found"}), 404

        recognized_student_id = student_ids[recognized_index]
        recognized_student = users.find_one({"_id": ObjectId(recognized_student_id)})

        # Check if attendance has already been marked for today
        today = datetime.utcnow().date()
        existing_attendance = db.attendance.find_one({
            "student_id": recognized_student_id,
            "date": today.isoformat()
        })

        if existing_attendance:
            return jsonify({
                "success": False,
                "message": "Attendance already marked for today",
                "student_name": recognized_student["full_name"]
            })

        # Return student info for confirmation
        return jsonify({
            "success": True,
            "message": "Student recognized",
            "student_name": recognized_student["full_name"],
            "student_id": recognized_student_id
        })

    except Exception as e:
        print(f"Error recognizing student: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while recognizing the student"}), 500

@staff_bp.route("/staff/confirm_attendance", methods=["POST"])
@login_required
def confirm_attendance():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        student_id = data.get("student_id")
        student_name = data.get("student_name")

        # Mark attendance
        attendance_record = {
            "student_id": student_id,
            "student_name": student_name,
            "date": datetime.utcnow().date().isoformat(),
            "time": datetime.utcnow().time().isoformat(),
            "marked_by": session["user"]["username"]
        }

        db.attendance.insert_one(attendance_record)

        return jsonify({
            "success": True,
            "message": "Attendance marked successfully",
            "student_name": student_name
        })
    except Exception as e:
        print(f"Error marking attendance: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while marking attendance"}), 500

from flask import jsonify, request
from datetime import datetime, timedelta

@staff_bp.route("/staff/get_attendance", methods=["GET"])
@login_required
def get_attendance():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({"success": False, "message": "Date parameter is required"}), 400

        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Get all students
        all_students = list(users.find({"role": "student"}, {"_id": 1, "username": 1}))

        # Get attendance records for the selected date
        attendance_records = list(db.attendance.find({"date": selected_date.isoformat()}))

        # Create a dictionary of present students
        present_students = {str(record["student_id"]): record for record in attendance_records}

        # Prepare the attendance list
        attendance_list = []
        for student in all_students:
            student_id = str(student["_id"])
            if student_id in present_students:
                status = "Present"
            else:
                status = "Absent"
            
            attendance_list.append({
                "student_name": student["username"],
                "status": status
            })

        return jsonify({
            "success": True,
            "attendance": attendance_list
        })

    except Exception as e:
        print(f"Error fetching attendance: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while fetching attendance"}), 500

@staff_bp.route("/staff/security_check", methods=["POST"])
@login_required
def security_check():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        image_data = request.json.get("image_data")
        ADMIN_EMAIL = "abhijithsnair2025@mca.ajce.in"

        # Get all user face encodings (both students and staff)
        all_users = list(users.find({"face_encoding": {"$exists": True}}))
        known_face_encodings = [np.array(user["face_encoding"]) for user in all_users]
        user_ids = [str(user["_id"]) for user in all_users]

        # Recognize the face
        recognized_index = recognize_face(image_data, known_face_encodings)

        current_time = datetime.utcnow()
        location = "Main Entrance"  # You can make this dynamic if needed

        if recognized_index is None:
            # Check if we can send notification (5 minute cooldown for unrecognized alerts)
            if can_send_notification("unrecognized_person"):
                send_email(
                    to_email=ADMIN_EMAIL,
                    subject="⚠️ Security Alert - Unrecognized Person Detected",
                    body=f"""
                    Security Alert!
                    
                    An unrecognized person was detected by the security system.
                    Location: {location}
                    Time: {current_time}
                    Reported by: {session['user']['username']}
                    
                    Please review the attached image and take necessary action.
                    """,
                    image_data=image_data
                )

            return jsonify({
                "success": False,
                "message": "Unrecognized person detected. Admin has been notified."
            })

        recognized_user_id = user_ids[recognized_index]
        recognized_user = users.find_one({"_id": ObjectId(recognized_user_id)})

        # Send notification for authorized entry (15 minute cooldown per user)
        if can_send_notification(f"authorized_entry_{recognized_user_id}", cooldown_minutes=15):
            send_email(
                to_email=ADMIN_EMAIL,
                subject="✅ Security Update - Authorized Entry",
                body=f"""
                Authorized Entry Detected
                
                Person: {recognized_user['full_name']}
                Role: {recognized_user['role']}
                Location: {location}
                Time: {current_time}
                Verified by: {session['user']['username']}
                
                This is an automated notification for security logging purposes.
                """,
                image_data=image_data
            )

        return jsonify({
            "success": True,
            "person_name": recognized_user["full_name"],
            "role": recognized_user["role"]
        })

    except Exception as e:
        print(f"Error in security check: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred during security check"}), 500

@staff_bp.route("/staff/get_request_details/<request_id>", methods=["GET"])
@login_required
def get_request_details(request_id):
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        # Convert string ID to ObjectId
        request_id = ObjectId(request_id)
        
        # Find the request in the database
        request_details = db.inventory_requests.find_one({"_id": request_id})
        
        if not request_details:
            return jsonify({"success": False, "message": "Request not found"}), 404
        
        # Convert ObjectId to string for JSON serialization
        request_details["_id"] = str(request_details["_id"])
        
        # Convert datetime to ISO format string
        if "timestamp" in request_details:
            request_details["timestamp"] = request_details["timestamp"].isoformat()
        
        return jsonify({
            "success": True,
            "request": request_details
        })
        
    except Exception as e:
        print(f"Error fetching request details: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Error fetching request details"
        }), 500

@staff_bp.route("/staff/update_request_status", methods=["POST"])
@login_required
def update_request_status():
    if session["user"]["role"] != "staff":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        request_id = data.get("requestId")
        new_status = data.get("status")

        if not all([request_id, new_status]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # Validate status
        valid_statuses = ["pending", "ordered", "delivered"]
        if new_status not in valid_statuses:
            return jsonify({"success": False, "message": "Invalid status"}), 400

        # Convert string ID to ObjectId
        request_id = ObjectId(request_id)

        # Update the request status
        result = db.inventory_requests.update_one(
            {"_id": request_id},
            {"$set": {
                "status": new_status,
                "updated_at": datetime.utcnow()
            }}
        )

        if result.modified_count > 0:
            return jsonify({
                "success": True,
                "message": f"Status updated to {new_status}"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Request not found or status not changed"
            }), 404

    except Exception as e:
        print(f"Error updating request status: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Error updating request status"
        }), 500