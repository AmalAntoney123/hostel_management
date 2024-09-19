from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    request,
    jsonify,
)
from utils import login_required
from datetime import datetime, timedelta
from config import db, users
from bson import ObjectId
import traceback
import calendar
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from dateutil.tz import tzutc


student_bp = Blueprint("student", __name__)


@student_bp.route("/student_dashboard")
@login_required
def student_dashboard():
    if session["user"]["role"] != "student":
        return redirect(url_for("index"))
    user_id = ObjectId(session["user"]["_id"])
    user = users.find_one({"_id": user_id})
    active_tab = request.args.get('active_tab', 'dashboard')
    return render_template("student_dashboard.html", user=user, active_tab=active_tab)


@student_bp.route("/student/submit_complaint", methods=["POST"])
@login_required
def student_submit_complaint():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        subject = data.get("subject")
        description = data.get("description")

        if not all([subject, description]):
            return (
                jsonify({"success": False, "message": "Missing required fields"}),
                400,
            )

        complaint = {
            "user_id": session["user"]["username"],
            "user_role": "student",
            "subject": subject,
            "description": description,
            "status": "pending",
            "timestamp": datetime.utcnow(),
            "admin_comment": "",
        }

        result = db.complaints.insert_one(complaint)

        if result.inserted_id:
            return jsonify(
                {"success": True, "message": "Complaint submitted successfully"}
            )
        else:
            return (
                jsonify({"success": False, "message": "Failed to submit complaint"}),
                500,
            )

    except Exception as e:
        print(f"Error submitting complaint: {str(e)}")  # Log the error
        return (
            jsonify(
                {
                    "success": False,
                    "message": "An error occurred while submitting the complaint",
                }
            ),
            500,
        )


@student_bp.route("/student/get_user_complaints", methods=["GET"])
@login_required
def student_get_user_complaints():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    complaints = list(db.complaints.find({"user_id": session["user"]["username"]}))
    for complaint in complaints:
        complaint["_id"] = str(complaint["_id"])
        complaint["timestamp"] = complaint["timestamp"].isoformat()

    return jsonify({"success": True, "complaints": complaints})


@student_bp.route("/student/get_blocks", methods=["GET"])
@login_required
def get_blocks():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    blocks = list(db.blocks.find({}, {"name": 1}))
    for block in blocks:
        block["_id"] = str(block["_id"])
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
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Student ID not found in session. Please log out and log in again.",
                    }
                ),
                400,
            )

        print(f"Searching for room assignment with student_id: {student_id}")
        room_assignment = db.room_assignments.find_one({"student_id": str(student_id)})

        if room_assignment:
            room_assignment["_id"] = str(room_assignment["_id"])
            print(f"Room assignment found: {room_assignment}")
            return jsonify({"success": True, "room_info": room_assignment})
        else:
            print("No room assignment found")
            return jsonify(
                {"success": True, "message": "No room assigned", "room_info": None}
            )
    except Exception as e:
        print(f"Error in get_current_room_info: {str(e)}")
        print(traceback.format_exc())
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"An error occurred while fetching room information: {str(e)}",
                }
            ),
            500,
        )


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


@student_bp.route(
    "/student/get_available_rooms/<block_id>/<int:floor_index>", methods=["GET"]
)
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
            room_numbers = floor[
                f"{room_type}{'Attached' if is_attached else 'NonAttached'}RoomNumbers"
            ]
            for room_number in room_numbers:
                occupancy = db.room_assignments.count_documents(
                    {
                        "block_id": str(block_id),
                        "floor_index": floor_index,
                        "room_number": room_number,
                    }
                )
                if occupancy < capacity:
                    rooms.append(
                        {
                            "number": room_number,
                            "type": room_type,
                            "attached": is_attached,
                            "available_beds": capacity - occupancy,
                        }
                    )

    return jsonify({"success": True, "rooms": rooms})


@student_bp.route("/student/request_room_change", methods=["POST"])
@login_required
def request_room_change():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    student_id = session["user"]["_id"]
    student_name = session["user"].get(
        "username", "Unknown"
    )  # Use username instead of full_name

    room_change_request = {
        "student_id": str(student_id),
        "student_name": student_name,
        "block_id": data["blockId"],
        "floor_index": int(data["floorIndex"]),
        "room_number": data["roomNumber"],
        "reason": data["reason"],
        "status": "pending",
        "created_at": datetime.utcnow(),
    }

    result = db.room_change_requests.insert_one(room_change_request)
    if result.inserted_id:
        return jsonify(
            {"success": True, "message": "Room change request submitted successfully"}
        )
    else:
        return jsonify(
            {"success": False, "message": "Error submitting room change request"}
        )


@student_bp.route("/student/get_room_change_status", methods=["GET"])
@login_required
def get_room_change_status():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    student_id = session["user"]["_id"]
    request = db.room_change_requests.find_one(
        {
            "student_id": str(student_id),
            "status": {"$in": ["pending", "approved", "rejected"]},
        },
        sort=[("created_at", -1)],
    )

    if request:
        request["_id"] = str(request["_id"])
        request["created_at"] = request["created_at"].isoformat()
        block = db.blocks.find_one({"_id": ObjectId(request["block_id"])})
        request["block_name"] = block["name"] if block else "Unknown"
        return jsonify({"success": True, "request": request})
    else:
        return jsonify({"success": True, "request": None})


@student_bp.route("/student/submit_gatepass", methods=["POST"])
@login_required
def submit_gatepass():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        reason = data.get("reason")
        departure_time = data.get("departureTime")
        return_time = data.get("returnTime")

        missing_fields = []
        if not reason:
            missing_fields.append("reason")
        if not departure_time:
            missing_fields.append("departureTime")
        if not return_time:
            missing_fields.append("returnTime")

        if missing_fields:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Missing required fields: {', '.join(missing_fields)}",
                    }
                ),
                400,
            )

        gatepass = {
            "student_id": session["user"]["_id"],
            "student_name": session["user"]["username"],
            "reason": reason,
            "departure_time": datetime.fromisoformat(departure_time),
            "return_time": datetime.fromisoformat(return_time),
            "status": "pending",
            "submitted_at": datetime.utcnow(),
        }

        result = db.gatepasses.insert_one(gatepass)

        if result.inserted_id:
            return jsonify(
                {"success": True, "message": "Gatepass submitted successfully"}
            )
        else:
            return (
                jsonify({"success": False, "message": "Failed to submit gatepass"}),
                500,
            )

    except Exception as e:
        print(f"Error submitting gatepass: {str(e)}")
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"An error occurred while submitting the gatepass: {str(e)}",
                }
            ),
            500,
        )


@student_bp.route("/student/get_student_gatepasses", methods=["GET"])
@login_required
def get_student_gatepasses():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    gatepasses = list(db.gatepasses.find({"student_id": session["user"]["_id"]}))
    for gatepass in gatepasses:
        gatepass["_id"] = str(gatepass["_id"])
        gatepass["departure_time"] = gatepass["departure_time"].isoformat()
        gatepass["return_time"] = gatepass["return_time"].isoformat()
        gatepass["submitted_at"] = gatepass["submitted_at"].isoformat()

    return jsonify({"success": True, "gatepasses": gatepasses})


@student_bp.route("/student/get_fee_info", methods=["GET"])
@login_required
def get_fee_info():
    try:
        if session["user"]["role"] != "student":
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        fee_settings = db.fee_settings.find_one()
        if not fee_settings:
            return jsonify({"success": False, "message": "Fee settings not found"}), 404

        student_id = session["user"]["_id"]
        student = users.find_one({"_id": ObjectId(student_id)})
        if not student:
            return jsonify({"success": False, "message": "Student not found"}), 404

        join_date = student.get("join_date")
        if not join_date:
            return jsonify({"success": False, "message": "Student join date not found"}), 404

        join_date = parse(join_date)
        current_date = datetime.now(tzutc())
        upcoming_payments = []

        if join_date <= current_date:
            # Calculate current month's mess fee
            current_mess_fee_due_date = get_next_mess_fee_due_date(current_date, fee_settings["messFeeDay"], 0)
            current_mess_fee_amount = fee_settings["messFee"]
            current_mess_fee_late_amount = calculate_late_fee(current_mess_fee_due_date, current_date, fee_settings["messFeeLateFee"])
            
            current_month_name = current_mess_fee_due_date.strftime("%B %Y")
            current_description = f"Mess Fee {current_month_name}"
            
            if not is_payment_made(student_id, current_description, current_mess_fee_due_date):
                upcoming_payments.append({
                    "dueDate": current_mess_fee_due_date.isoformat(),
                    "description": current_description,
                    "amount": current_mess_fee_amount,
                    "lateAmount": current_mess_fee_late_amount,
                    "status": "Overdue" if current_date > current_mess_fee_due_date else "Pending"
                })

            # Check for unpaid mess fees from previous months
            for i in range(1, 12):
                prev_mess_fee_due_date = get_next_mess_fee_due_date(current_date, fee_settings["messFeeDay"], -i)
                if prev_mess_fee_due_date < join_date:
                    break
                
                prev_month_name = prev_mess_fee_due_date.strftime("%B %Y")
                prev_description = f"Mess Fee {prev_month_name}"
                
                if not is_payment_made(student_id, prev_description, prev_mess_fee_due_date):
                    prev_mess_fee_late_amount = calculate_late_fee(prev_mess_fee_due_date, current_date, fee_settings["messFeeLateFee"])
                    upcoming_payments.append({
                        "dueDate": prev_mess_fee_due_date.isoformat(),
                        "description": prev_description,
                        "amount": fee_settings["messFee"],
                        "lateAmount": prev_mess_fee_late_amount,
                        "status": "Overdue"
                    })
                else:
                    break

            # Calculate hostel rent
            rent_due_date = fee_settings["rentDueDate"].replace(year=current_date.year, tzinfo=tzutc())
            if rent_due_date < current_date:
                rent_due_date = rent_due_date.replace(year=current_date.year + 1)
            
            if join_date <= rent_due_date:
                rent_fee_amount = fee_settings["rentFee"]
                rent_fee_late_amount = calculate_late_fee(rent_due_date, current_date, fee_settings["rentFeeLateFee"])
                
                description = f"Hostel Rent {rent_due_date.year}"
                
                if not is_payment_made(student_id, description, rent_due_date):
                    upcoming_payments.append({
                        "dueDate": rent_due_date.isoformat(),
                        "description": description,
                        "amount": rent_fee_amount,
                        "lateAmount": rent_fee_late_amount,
                        "status": "Overdue" if current_date > rent_due_date else "Pending"
                    })

        fee_info = {
            "joinDate": join_date.isoformat(),
            "messFeeDay": fee_settings["messFeeDay"],
            "messFee": fee_settings["messFee"],
            "rentDueDate": fee_settings["rentDueDate"].strftime("%B %d"),
            "rentFee": fee_settings["rentFee"],
            "upcomingPayments": upcoming_payments
        }

        return jsonify({"success": True, "feeInfo": fee_info})
    except Exception as e:
        print(f"Error in get_fee_info: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


def get_next_mess_fee_due_date(current_date, due_day, months_ahead=0):
    # Start with the current month
    next_date = current_date.replace(day=1) + relativedelta(months=months_ahead)

    # Set the day to the due day
    next_date = next_date.replace(
        day=min(due_day, calendar.monthrange(next_date.year, next_date.month)[1])
    )

    return next_date


def calculate_late_fee(due_date, current_date, daily_late_fee):
    if current_date <= due_date:
        return 0
    days_late = (current_date - due_date).days
    return min(days_late * daily_late_fee, 500)  # Cap the late fee at 500 Rs


def is_payment_made(student_id, description, due_date):
    payment = db.payments.find_one(
        {
            "student_id": student_id,
            "description": description,
            "payment_date": {
                "$gte": due_date - timedelta(days=30),
                "$lte": datetime.utcnow(),
            },
        }
    )
    return payment is not None


@student_bp.route("/student/get_notices", methods=["GET"])
@login_required
def get_notices():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    notices = list(db.notices.find({"$or": [{"target": "all"}, {"target": "students"}]}).sort("posted_date", -1))
    for notice in notices:
        notice["_id"] = str(notice["_id"])
        notice["posted_date"] = notice["posted_date"].isoformat()

    return jsonify({"success": True, "notices": notices})

@student_bp.route("/profile")
@login_required
def profile():
    user_id = ObjectId(session["user"]["_id"])
    user = users.find_one({"_id": user_id})
    return render_template("student/profile.html", user=user)