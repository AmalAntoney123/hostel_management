from flask import Flask, render_template
from config import app_config
from auth import auth_bp
from admin import admin_bp
from student import student_bp
from staff import staff_bp

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config.from_object(app_config)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)
app.register_blueprint(staff_bp)

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)