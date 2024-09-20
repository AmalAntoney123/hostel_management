import stripe
from flask import Blueprint, request, jsonify, session, url_for, render_template, redirect
from utils import login_required
from config import db
import os
from datetime import datetime
from bson import ObjectId

payment_bp = Blueprint('payment', __name__)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

@payment_bp.route("/create_payment_session", methods=["POST"])
@login_required
def create_payment_session():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    amount = data.get('amount')
    description = data.get('description')
    
    if not amount or not description:
        return jsonify({"success": False, "message": "Amount and description are required"}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(float(amount) * 100),
                    'product_data': {
                        'name': description,
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment.payment_cancel', _external=True),
            client_reference_id=session['user']['_id']
        )
        return jsonify({"success": True, "url": checkout_session.url})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@payment_bp.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    if session["user"]["role"] not in ["student", "parent"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    data = request.json
    amount = data.get('amount')
    description = data.get('description')
    
    if not amount or not description:
        return jsonify({"success": False, "message": "Amount and description are required"}), 400

    try:
        # If the user is a parent, we need to get the associated student's ID
        if session["user"]["role"] == "parent":
            parent = db.users.find_one({"_id": ObjectId(session["user"]["_id"])})
            if not parent or "associated_student" not in parent:
                return jsonify({"success": False, "message": "No associated student found"}), 400
            student_id = str(parent["associated_student"])
        else:
            student_id = session['user']['_id']

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'inr',
                    'unit_amount': int(float(amount) * 100),
                    'product_data': {
                        'name': description,
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment.payment_cancel', _external=True),
            client_reference_id=student_id,
            metadata={'description': description}  
        )
        return jsonify({"success": True, "checkoutUrl": checkout_session.url})
    except Exception as e:
        print(f"Error in create_checkout_session: {str(e)}")  # Add this line for debugging
        return jsonify({"success": False, "message": str(e)}), 500

@payment_bp.route("/payment_success")
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if session_id:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status == 'paid':
            update_payment_status(checkout_session)
    
    # Redirect based on user role
    if session["user"]["role"] == "student":
        return redirect(url_for('student.student_dashboard', active_tab='fees'))
    elif session["user"]["role"] == "parent":
        return redirect(url_for('parent.parent_dashboard', active_tab='fees'))
    else:
        return redirect(url_for('index'))

@payment_bp.route("/payment_cancel")
@login_required
def payment_cancel():
    # Redirect based on user role
    if session["user"]["role"] == "student":
        return redirect(url_for('student.student_dashboard', active_tab='fees'))
    elif session["user"]["role"] == "parent":
        return redirect(url_for('parent.parent_dashboard', active_tab='fees'))
    else:
        return redirect(url_for('index'))

def update_payment_status(checkout_session):
    student_id = checkout_session.client_reference_id
    amount = checkout_session.amount_total / 100  # Convert cents to dollars
    description = checkout_session.metadata.get('description', '').strip()  # Ensure description is retrieved

    payment = {
        'student_id': student_id,
        'amount': amount,
        'description': description,  # Ensure description is included
        'payment_date': datetime.utcnow(),
        'stripe_session_id': checkout_session.id
    }

    db.payments.insert_one(payment)

    # Update student_fees collection only if description is valid
    if description:  # Check if description is not empty
        if 'Mess Fee' in description:
            db.student_fees.update_one(
                {'student_id': student_id},
                {'$set': {'last_mess_fee_payment': datetime.utcnow()}}
            )
        elif 'Hostel Rent' in description:
            db.student_fees.update_one(
                {'student_id': student_id},
                {'$set': {'last_rent_payment': datetime.utcnow()}}
            )
            
@payment_bp.route("/student/get_past_payments", methods=["GET"])
@login_required
def get_past_payments():
    if session["user"]["role"] != "student":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    student_id = session["user"]["_id"]
    print(f"Fetching past payments for student ID: {student_id}")

    try:
        # Retrieve past payments for the student
        past_payments = list(db.payments.find({"student_id": student_id}))
        print(f"Found {len(past_payments)} past payments")

        # Format the payments for the response
        formatted_payments = []
        for payment in past_payments:
            formatted_payment = {
                "payment_date": payment["payment_date"].isoformat(),
                "description": payment.get("description", "N/A"),
                "amount": payment["amount"]
            }
            formatted_payments.append(formatted_payment)

        print("Formatted payments:", formatted_payments)
        return jsonify({"success": True, "pastPayments": formatted_payments})
    except Exception as e:
        print(f"Error in get_past_payments: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500