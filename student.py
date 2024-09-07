from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from utils import login_required
from datetime import datetime
from config import db
from bson import ObjectId
import traceback

student_bp = Blueprint('student', __name__)

@student_bp.route("/student_dashboard")
@login_required
def student_dashboard():
    if session["user"]["role"] != "student":
        return redirect(url_for("index"))
    return render_template("student_dashboard.html")

@student_bp.route("/student/submit_complaint", methods=["POST"])
@login_required
def student_submit_complaint():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        subject = data.get('subject')
        description = data.get('description')

        if not all([subject, description]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        complaint = {
            "user_id": session["user"]["username"],
            "user_role": "student",
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

@student_bp.route("/student/get_user_complaints", methods=["GET"])
@login_required
def student_get_user_complaints():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    complaints = list(db.complaints.find({"user_id": session["user"]["username"]}))
    for complaint in complaints:
        complaint['_id'] = str(complaint['_id'])
        complaint['timestamp'] = complaint['timestamp'].isoformat()

    return jsonify({"success": True, "complaints": complaints})

@student_bp.route("/student/get_blocks", methods=["GET"])
@login_required
def get_blocks():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    blocks = list(db.blocks.find({}, {"name": 1}))
    for block in blocks:
        block['_id'] = str(block['_id'])
    return jsonify({"success": True, "blocks": blocks})

@student_bp.route("/student/get_current_room_info", methods=["GET"])
@login_required
def get_current_room_info():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        student_id = session["user"].get("_id")
        if not student_id:
            print("Student ID not found in session")
            print("Session user data:", session["user"])
            return jsonify({"success": False, "message": "Student ID not found in session. Please log out and log in again."}), 400

        print(f"Searching for room assignment with student_id: {student_id}")
        room_assignment = db.room_assignments.find_one({"student_id": str(student_id)})
        
        if room_assignment:
            room_assignment['_id'] = str(room_assignment['_id'])
            print(f"Room assignment found: {room_assignment}")
            return jsonify({"success": True, "room_info": room_assignment})
        else:
            print("No room assignment found")
            return jsonify({"success": True, "message": "No room assigned", "room_info": None})
    except Exception as e:
        print(f"Error in get_current_room_info: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": f"An error occurred while fetching room information: {str(e)}"}), 500

@student_bp.route("/student/get_floors/<block_id>", methods=["GET"])
@login_required
def get_floors(block_id):
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    block = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not block:
        return jsonify({"success": False, "message": "Block not found"}), 404

    floors = [{"index": i, "number": i + 1} for i in range(len(block["floors"]))]
    return jsonify({"success": True, "floors": floors})

@student_bp.route("/student/get_available_rooms/<block_id>/<int:floor_index>", methods=["GET"])
@login_required
def get_available_rooms(block_id, floor_index):
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    block = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not block or floor_index >= len(block["floors"]):
        return jsonify({"success": False, "message": "Block or floor not found"}), 404

    floor = block["floors"][floor_index]
    rooms = []
    for room_type in ["single", "double", "triple"]:
        capacity = 1 if room_type == "single" else (2 if room_type == "double" else 3)
        
        for is_attached in [True, False]:
            room_numbers = floor[f"{room_type}{'Attached' if is_attached else 'NonAttached'}RoomNumbers"]
            for room_number in room_numbers:
                occupancy = db.room_assignments.count_documents({
                    "block_id": str(block_id),
                    "floor_index": floor_index,
                    "room_number": room_number
                })
                if occupancy < capacity:
                    rooms.append({
                        "number": room_number,
                        "type": room_type,
                        "attached": is_attached,
                        "available_beds": capacity - occupancy
                    })

    return jsonify({"success": True, "rooms": rooms})

@student_bp.route("/student/request_room_change", methods=["POST"])
@login_required
def request_room_change():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    student_id = session["user"]["_id"]
    student_name = session["user"].get("username", "Unknown")  # Use username instead of full_name

    room_change_request = {
        "student_id": str(student_id),
        "student_name": student_name,
        "block_id": data["blockId"],
        "floor_index": int(data["floorIndex"]),
        "room_number": data["roomNumber"],
        "reason": data["reason"],
        "status": "pending",
        "created_at": datetime.utcnow()
    }

    result = db.room_change_requests.insert_one(room_change_request)
    if result.inserted_id:
        return jsonify({"success": True, "message": "Room change request submitted successfully"})
    else:
        return jsonify({"success": False, "message": "Error submitting room change request"})

@student_bp.route("/student/get_room_change_status", methods=["GET"])
@login_required
def get_room_change_status():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    student_id = session["user"]["_id"]
    request = db.room_change_requests.find_one(
        {"student_id": str(student_id), "status": {"$in": ["pending", "approved", "rejected"]}},
        sort=[("created_at", -1)]
    )

    if request:
        request["_id"] = str(request["_id"])
        request["created_at"] = request["created_at"].isoformat()
        block = db.blocks.find_one({"_id": ObjectId(request["block_id"])})
        request["block_name"] = block["name"] if block else "Unknown"
        return jsonify({"success": True, "request": request})
    else:
        return jsonify({"success": True, "request": None})