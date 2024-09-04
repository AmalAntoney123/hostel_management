from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
users = db.users
rooms = db.rooms
fees = db.fees
students = db["students"]

def create_admin():
    username = input("Enter admin username: ")
    password = input("Enter admin password: ")
    
    # Check if the username already exists
    if users.find_one({"username": username}):
        print("Error: Username already exists.")
        return
    
    # Create admin user
    admin_user = {
        "username": username,
        "password": generate_password_hash(password),
        "role": "admin"
    }
    
    # Insert the admin user into the database
    result = users.insert_one(admin_user)
    
    if result.inserted_id:
        print(f"Admin user '{username}' created successfully.")
    else:
        print("Error: Failed to create admin user.")

if __name__ == "__main__":
    create_admin()
