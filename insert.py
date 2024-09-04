from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import bcrypt

# Load environment variables
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('DB_NAME')]

# Clear existing data (optional)
db.users.delete_many({})
db.rooms.delete_many({})
db.fees.delete_many({})

# Function to hash password
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Insert sample users with hashed passwords
users = [
    {
        "_id": ObjectId(),
        "username": "admin1",
        "password": hash_password("admin123"),
        "role": "admin",
        "full_name": "Admin User",
        "email": "admin@hostelcloudsuite.com"
    },
    {
        "_id": ObjectId(),
        "username": "staff1",
        "password": hash_password("staff123"),
        "role": "staff",
        "full_name": "Staff Member",
        "email": "staff@hostelcloudsuite.com"
    },
    {
        "_id": ObjectId(),
        "username": "student1",
        "password": hash_password("student123"),
        "role": "student",
        "full_name": "John Doe",
        "email": "john@example.com"
    },
    {
        "_id": ObjectId(),
        "username": "student2",
        "password": hash_password("student456"),
        "role": "student",
        "full_name": "Jane Smith",
        "email": "jane@example.com"
    }
]

db.users.insert_many(users)

# Insert sample rooms
rooms = [
    {
        "room_number": "A101",
        "capacity": 2,
        "occupied": 1,
        "residents": [users[2]["_id"]]  # John Doe
    },
    {
        "room_number": "A102",
        "capacity": 2,
        "occupied": 1,
        "residents": [users[3]["_id"]]  # Jane Smith
    },
    {
        "room_number": "B201",
        "capacity": 3,
        "occupied": 0,
        "residents": []
    }
]

db.rooms.insert_many(rooms)

# Insert sample fees
fees = [
    {
        "student_id": users[2]["_id"],  # John Doe
        "amount": 500.00,
        "due_date": datetime.now() + timedelta(days=30),
        "paid": False,
        "payment_date": None
    },
    {
        "student_id": users[3]["_id"],  # Jane Smith
        "amount": 500.00,
        "due_date": datetime.now() + timedelta(days=30),
        "paid": True,
        "payment_date": datetime.now() - timedelta(days=5)
    }
]

db.fees.insert_many(fees)

print("Sample data inserted successfully with encrypted passwords!")