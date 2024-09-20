from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from bson import ObjectId
from config import db, users
from utils import login_required
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import calendar
import traceback

parent_bp = Blueprint("parent", __name__)

@parent_bp.route("/parent_dashboard")
@login_required
def parent_dashboard():
    if session["user"]["role"] != "parent":
        return redirect(url_for("index"))
    
    parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
    
    if parent and "associated_student" in parent:
        student = users.find_one({"_id": ObjectId(parent["associated_student"])})
    else:
        student = None

    return render_template("parent_dashboard.html", parent=parent, student=student)

@parent_bp.route("/parent/get_student_attendance", methods=["GET"])
@login_required
def get_student_attendance():
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
        if not parent or "associated_student" not in parent:
            return jsonify({"success": False, "message": "No associated student found"}), 400

        student_id = parent["associated_student"]
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({"success": False, "message": "Start and end dates are required"}), 400

        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        attendance_records = list(db.attendance.find({
            "student_id": str(student_id),
            "date": {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat()
            }
        }))

        calendar_data = []
        current_date = start_date
        while current_date <= end_date:
            is_present = any(record["date"] == current_date.isoformat() for record in attendance_records)
            calendar_data.append({
                "date": current_date.isoformat(),
                "status": "present" if is_present else "absent"
            })
            current_date += timedelta(days=1)

        return jsonify({
            "success": True,
            "attendance": calendar_data
        })
    except Exception as e:
        print(f"Error fetching student attendance: {str(e)}")
        return jsonify({"success": False, "message": "An error occurred while fetching attendance"}), 500

@parent_bp.route("/parent/get_fee_info", methods=["GET"])
@login_required
def get_parent_fee_info():
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
        if not parent:
            return jsonify({"success": False, "message": "Parent not found"}), 404

        if "associated_student" not in parent:
            return jsonify({"success": False, "message": "No associated student found"}), 400

        student_id = parent["associated_student"]
        student = users.find_one({"_id": ObjectId(student_id)})
        if not student:
            return jsonify({"success": False, "message": "Associated student not found"}), 404

        fee_settings = db.fee_settings.find_one()
        if not fee_settings:
            return jsonify({"success": False, "message": "Fee settings not found"}), 404

        join_date = student.get("join_date")
        if not join_date:
            return jsonify({"success": False, "message": "Student join date not found"}), 404

        # Ensure join_date is timezone-aware
        if isinstance(join_date, datetime):
            if join_date.tzinfo is None:
                join_date = join_date.replace(tzinfo=timezone.utc)
        else:
            # If it's a string, parse it and make it timezone-aware
            join_date = datetime.fromisoformat(join_date).replace(tzinfo=timezone.utc)

        current_date = datetime.now(timezone.utc)
        upcoming_payments = []

        if join_date <= current_date:
            # Calculate current month's mess fee
            current_mess_fee_due_date = get_next_mess_fee_due_date(current_date, fee_settings["messFeeDay"], 0)
            current_mess_fee_amount = fee_settings["messFee"]
            current_mess_fee_late_amount = calculate_late_fee(current_mess_fee_due_date, current_date, fee_settings["messFeeLateFee"])
            
            current_month_name = current_mess_fee_due_date.strftime("%B %Y")
            current_description = f"Mess Fee {current_month_name}"
            
            if not is_payment_made(str(student_id), current_description, current_mess_fee_due_date):
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
                
                if not is_payment_made(str(student_id), prev_description, prev_mess_fee_due_date):
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
            rent_due_date = fee_settings["rentDueDate"].replace(year=current_date.year, tzinfo=timezone.utc)
            if rent_due_date < current_date:
                rent_due_date = rent_due_date.replace(year=current_date.year + 1)
            
            if join_date <= rent_due_date:
                rent_fee_amount = fee_settings["rentFee"]
                rent_fee_late_amount = calculate_late_fee(rent_due_date, current_date, fee_settings["rentFeeLateFee"])
                
                description = f"Hostel Rent {rent_due_date.year}"
                
                if not is_payment_made(str(student_id), description, rent_due_date):
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
        print(f"Error in get_parent_fee_info: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

def get_next_mess_fee_due_date(current_date, due_day, months_ahead=0):
    next_date = current_date.replace(day=1, tzinfo=timezone.utc) + relativedelta(months=months_ahead)
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
                "$lte": datetime.now(timezone.utc),
            },
        }
    )
    return payment is not None

@parent_bp.route("/parent/get_past_payments", methods=["GET"])
@login_required
def get_parent_past_payments():
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
        if not parent or "associated_student" not in parent:
            return jsonify({"success": False, "message": "No associated student found"}), 400

        student_id = parent["associated_student"]
        past_payments = list(db.payments.find({"student_id": str(student_id)}).sort("payment_date", -1))

        for payment in past_payments:
            payment["_id"] = str(payment["_id"])
            payment["payment_date"] = payment["payment_date"].isoformat()

        return jsonify({"success": True, "pastPayments": past_payments})
    except Exception as e:
        print(f"Error in get_parent_past_payments: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500


@parent_bp.route("/parent/get_student_outing_history", methods=["GET"])
@login_required
def get_student_outing_history():
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
        print(f"Parent: {parent}")  # Debug log
        if not parent or "associated_student" not in parent:
            return jsonify({"success": False, "message": "No associated student found"}), 400

        student_id = parent["associated_student"]
        print(f"Associated student ID: {student_id}")  # Debug log
        
        # Convert ObjectId to string for comparison
        student_id_str = str(student_id)
        
        outings = list(db.gatepasses.find({"student_id": student_id_str}).sort("submitted_at", -1))
        print(f"Outings found: {len(outings)}")  # Debug log

        for outing in outings:
            outing["_id"] = str(outing["_id"])
            outing["departure_time"] = outing["departure_time"].isoformat()
            outing["return_time"] = outing["return_time"].isoformat()
            outing["submitted_at"] = outing["submitted_at"].isoformat()

        return jsonify({"success": True, "outings": outings})
    except Exception as e:
        print(f"Error in get_student_outing_history: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500
    
@parent_bp.route("/parent/get_pending_visitor_passes", methods=["GET"])
@login_required
def get_pending_visitor_passes():
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
        if not parent or "associated_student" not in parent:
            return jsonify({"success": False, "message": "No associated student found"}), 400

        student_id = parent["associated_student"]
        pending_passes = list(db.visitor_passes.find({
            "student_id": str(student_id),
            "status": "pending_parent"
        }))

        for pass_ in pending_passes:
            pass_["_id"] = str(pass_["_id"])
            pass_["visit_date"] = pass_["visit_date"].isoformat()
            pass_["submitted_at"] = pass_["submitted_at"].isoformat()

        return jsonify({"success": True, "pendingPasses": pending_passes})
    except Exception as e:
        print(f"Error fetching pending visitor passes: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

@parent_bp.route("/parent/get_previous_visitor_passes", methods=["GET"])
@login_required
def get_previous_visitor_passes():
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        parent = users.find_one({"_id": ObjectId(session["user"]["_id"])})
        if not parent or "associated_student" not in parent:
            return jsonify({"success": False, "message": "No associated student found"}), 400

        student_id = parent["associated_student"]
        previous_passes = list(db.visitor_passes.find({
            "student_id": str(student_id),
            "status": {"$ne": "pending_parent"}
        }).sort("submitted_at", -1))

        for pass_ in previous_passes:
            pass_["_id"] = str(pass_["_id"])
            pass_["visit_date"] = pass_["visit_date"].isoformat()
            pass_["submitted_at"] = pass_["submitted_at"].isoformat()

        return jsonify({"success": True, "previousPasses": previous_passes})
    except Exception as e:
        print(f"Error fetching previous visitor passes: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

@parent_bp.route("/parent/approve_visitor_pass/<pass_id>", methods=["POST"])
@login_required
def approve_visitor_pass(pass_id):
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        result = db.visitor_passes.update_one(
            {"_id": ObjectId(pass_id)},
            {
                "$set": {
                    "status": "pending_admin",
                    "parent_approval": {
                        "approved": True,
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )

        if result.modified_count > 0:
            return jsonify({"success": True, "message": "Visitor pass approved successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to approve visitor pass"}), 400
    except Exception as e:
        print(f"Error approving visitor pass: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500

@parent_bp.route("/parent/reject_visitor_pass/<pass_id>", methods=["POST"])
@login_required
def reject_visitor_pass(pass_id):
    if session["user"]["role"] != "parent":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        result = db.visitor_passes.update_one(
            {"_id": ObjectId(pass_id)},
            {
                "$set": {
                    "status": "rejected",
                    "parent_approval": {
                        "approved": False,
                        "timestamp": datetime.utcnow()
                    }
                }
            }
        )

        if result.modified_count > 0:
            return jsonify({"success": True, "message": "Visitor pass rejected successfully"})
        else:
            return jsonify({"success": False, "message": "Failed to reject visitor pass"}), 400
    except Exception as e:
        print(f"Error rejecting visitor pass: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"}), 500