from flask import Flask, render_template, jsonify
from config import app_config
from auth import auth_bp
from admin import admin_bp
from student import student_bp
from staff import staff_bp
from payment import payment_bp
from parent import parent_bp
from student_dashboard import student_dashboard_bp
from parent_dashboard import parent_dashboard_bp
from admin_dashboard import admin_dashboard_bp
import os

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config.from_object(app_config)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)
app.register_blueprint(staff_bp)
app.register_blueprint(parent_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(student_dashboard_bp)
app.register_blueprint(parent_dashboard_bp)
app.register_blueprint(admin_dashboard_bp)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/get_stripe_key', methods=['GET'])
def get_stripe_key():
    stripe_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
    return jsonify(stripe_key=stripe_key)

if __name__ == "__main__":
    app.run(debug=True)