import stripe
from flask import Blueprint, request, jsonify, session, url_for, render_template
from utils import login_required
from config import db
import os
from datetime import datetime

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

@payment_bp.route("/payment_success")
@login_required
def payment_success():
    session_id = request.args.get('session_id')
    if session_id:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status == 'paid':
            update_payment_status(checkout_session)
    return render_template('payment_success.html')

@payment_bp.route("/payment_cancel")
@login_required
def payment_cancel():
    return render_template('payment_cancel.html')

def update_payment_status(checkout_session):
    student_id = checkout_session.client_reference_id
    amount = checkout_session.amount_total / 100

    # Retrieve the session with line items expanded
    session_with_line_items = stripe.checkout.Session.retrieve(
        checkout_session.id,
        expand=['line_items']
    )

    # Get the description from the expanded line items
    description = ''
    if session_with_line_items.line_items and session_with_line_items.line_items.data:
        description = session_with_line_items.line_items.data[0].description

    if not student_id:
        print(f"Error: No student_id found for session {checkout_session.id}")
        return

    payment = {
        'student_id': student_id,
        'amount': amount,
        'description': description,
        'payment_date': datetime.utcnow(),
        'stripe_session_id': checkout_session.id
    }

    db.payments.insert_one(payment)

    # Update student_fees collection
    update_data = {}
    if 'Mess Fee' in description:
        update_data['last_mess_fee_payment'] = datetime.utcnow()
    elif 'Hostel Rent' in description:
        update_data['last_rent_payment'] = datetime.utcnow()

    if update_data:
        db.student_fees.update_one(
            {'student_id': student_id},
            {'$set': update_data},
            upsert=True
        )

    print(f"Payment updated for student {student_id}: {description}")