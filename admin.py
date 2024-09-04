from flask import Blueprint, redirect, render_template, request, jsonify, session, url_for
from werkzeug.security import generate_password_hash
from config import users, db  # Import the db object from your config file
from utils import login_required
import pandas as pd
import io
from bson import ObjectId, errors as bson_errors  # Import ObjectId for MongoDB
import traceback

admin_bp = Blueprint('admin', __name__)

# Add this line to define the room_assignments collection
room_assignments = db.room_assignments

@admin_bp.route("/admin_dashboard")
@login_required
def admin_dashboard():
    if session["user"]["role"] != "admin":
        return redirect(url_for("index"))
    return render_template("admin_dashboard.html")

@admin_bp.route("/add_user", methods=["POST"])
@login_required
def add_user():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    username = data.get("username")
    full_name = data.get("full_name")
    email = data.get("email")
    phone = data.get("phone")
    role = data.get("role")

    if not all([username, full_name, email, phone, role]):
        return {"success": False, "message": "Missing required fields"}, 400

    existing_user = users.find_one({"username": username})
    if existing_user:
        return {"success": False, "message": "Username already exists"}, 400

    password = f"{username}@{phone[-4:]}"
    hashed_password = generate_password_hash(password)

    new_user = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "role": role,
        "password": hashed_password,
        "is_active": True  # Add this line
    }

    users.insert_one(new_user)

    return {
        "success": True,
        "message": f"{role.capitalize()} added successfully",
        "username": username,
        "password": password
    }

@admin_bp.route("/get_users/<role>", methods=["GET"])
@login_required
def get_users(role):
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    if role not in ["student", "staff"]:
        return {"success": False, "message": "Invalid role"}, 400

    # Use inclusion projection instead of mixing inclusion and exclusion
    user_list = list(users.find(
        {"role": role}, 
        {"_id": 0, "username": 1, "full_name": 1, "email": 1, "phone": 1, "is_active": 1}
    ))
    return jsonify({"success": True, "users": user_list})

@admin_bp.route("/bulk_upload_users", methods=["POST"])
@login_required
def bulk_upload_users():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    if 'excelFile' not in request.files:
        return {"success": False, "message": "No file part"}, 400

    file = request.files['excelFile']
    user_type = request.form.get('userType')

    if file.filename == '':
        return {"success": False, "message": "No selected file"}, 400

    if user_type not in ['student', 'staff']:
        return {"success": False, "message": "Invalid user type"}, 400

    try:
        df = pd.read_excel(file) if file.filename.endswith(('.xls', '.xlsx')) else pd.read_csv(file)
        required_columns = ['username', 'full_name', 'email', 'phone']
        
        if not all(col in df.columns for col in required_columns):
            return {"success": False, "message": "Missing required columns"}, 400

        success_count = 0
        error_count = 0

        for _, row in df.iterrows():
            username = row['username']
            full_name = row['full_name']
            email = row['email']
            phone = str(row['phone'])

            existing_user = users.find_one({"username": username})
            if existing_user:
                error_count += 1
                continue

            password = f"{username}@{phone[-4:]}"
            hashed_password = generate_password_hash(password)

            new_user = {
                "username": username,
                "full_name": full_name,
                "email": email,
                "phone": phone,
                "role": user_type,
                "password": hashed_password,
                "is_active": True  # Add this line
            }

            users.insert_one(new_user)
            success_count += 1

        return {
            "success": True,
            "message": f"Uploaded {success_count} users successfully. {error_count} users failed."
        }

    except Exception as e:
        return {"success": False, "message": f"Error processing file: {str(e)}"}, 500

@admin_bp.route("/toggle_user_status", methods=["POST"])
@login_required
def toggle_user_status():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    username = data.get("username")
    role = data.get("role")

    if not username or role not in ["student", "staff"]:
        return {"success": False, "message": "Invalid request"}, 400

    user = users.find_one({"username": username, "role": role})
    if not user:
        return {"success": False, "message": "User not found"}, 404

    new_status = not user.get("is_active", True)
    users.update_one({"username": username}, {"$set": {"is_active": new_status}})

    return {"success": True, "message": f"User status updated to {'active' if new_status else 'disabled'}"}

@admin_bp.route("/reset_user_password", methods=["POST"])
@login_required
def reset_user_password():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    username = data.get("username")
    role = data.get("role")

    if not username or role not in ["student", "staff"]:
        return {"success": False, "message": "Invalid request"}, 400

    user = users.find_one({"username": username, "role": role})
    if not user:
        return {"success": False, "message": "User not found"}, 404

    new_password = f"{username}@{user['phone'][-4:]}"
    hashed_password = generate_password_hash(new_password)

    users.update_one({"username": username}, {"$set": {"password": hashed_password}})

    return {"success": True, "message": "Password reset successfully", "password": new_password}


@admin_bp.route("/add_block", methods=["POST"])
@login_required
def add_block():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    block_name = data.get("blockName")
    floors = data.get("floors")

    if not block_name or not floors:
        return {"success": False, "message": "Missing required fields"}, 400

    # Update the floor structure
    for floor in floors:
        for room_type in ['single', 'double', 'triple']:
            total_rooms = floor.get(f"{room_type}Rooms", 0)
            attached_rooms = floor.get(f"{room_type}AttachedRooms", 0)
            floor[f"{room_type}Rooms"] = total_rooms
            floor[f"{room_type}AttachedRooms"] = min(attached_rooms, total_rooms)

    new_block = {
        "name": block_name,
        "floors": floors
    }

    result = db.blocks.insert_one(new_block)

    return {
        "success": True,
        "message": "Block added successfully",
        "blockId": str(result.inserted_id)
    }

@admin_bp.route("/get_blocks", methods=["GET"])
@login_required
def get_blocks():
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        blocks = list(db.blocks.find())
        for block in blocks:
            block['_id'] = str(block['_id'])  # Convert ObjectId to string
            # Ensure each block has a 'floors' array
            if 'floors' not in block or not isinstance(block['floors'], list):
                block['floors'] = []
            # Ensure each floor has the required room count fields
            for floor in block['floors']:
                floor['singleRooms'] = floor.get('singleRooms', 0)
                floor['doubleRooms'] = floor.get('doubleRooms', 0)
                floor['tripleRooms'] = floor.get('tripleRooms', 0)
        
        print("Sending blocks:", blocks)  # Log the blocks being sent
        return jsonify({"success": True, "blocks": blocks})
    except Exception as e:
        print(f"Error in get_blocks: {str(e)}")  # Log any errors
        return jsonify({"success": False, "message": f"Error retrieving blocks: {str(e)}"}), 500

@admin_bp.route("/get_floors/<block_id>", methods=["GET"])
@login_required
def get_floors(block_id):
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    block = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not block:
        return {"success": False, "message": "Block not found"}, 404

    return jsonify({"success": True, "floors": block["floors"]})

@admin_bp.route("/get_available_rooms/<block_id>/<int:floor_index>", methods=["GET"])
@login_required
def get_available_rooms(block_id, floor_index):
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    block = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not block or floor_index >= len(block["floors"]):
        return {"success": False, "message": "Block or floor not found"}, 404

    floor = block["floors"][floor_index]
    rooms = []
    for room_type in ["single", "double", "triple"]:
        attached_rooms = floor[f"{room_type}AttachedRoomNumbers"]
        non_attached_rooms = floor[f"{room_type}NonAttachedRoomNumbers"]
        
        for room_number in attached_rooms:
            rooms.append({"number": room_number, "type": room_type, "attached": True})
        
        for room_number in non_attached_rooms:
            rooms.append({"number": room_number, "type": room_type, "attached": False})

    return jsonify({"success": True, "rooms": rooms})

@admin_bp.route("/copy_floor_layout/<block_id>", methods=["POST"])
@login_required
def copy_floor_layout(block_id):
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    data = request.json
    source_floor_index = data.get("sourceFloorIndex")
    target_floor_indices = data.get("targetFloorIndices")

    if source_floor_index is None or target_floor_indices is None:
        return {"success": False, "message": "Missing required fields"}, 400

    try:
        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if not block:
            return {"success": False, "message": "Block not found"}, 404

        if source_floor_index < 0 or source_floor_index >= len(block['floors']):
            return {"success": False, "message": "Invalid source floor index"}, 400

        source_floor = block['floors'][source_floor_index]

        for target_index in target_floor_indices:
            if target_index < 0 or target_index >= len(block['floors']):
                return {"success": False, "message": f"Invalid target floor index: {target_index + 1}"}, 400

            block['floors'][target_index] = source_floor.copy()

        result = db.blocks.update_one(
            {"_id": ObjectId(block_id)},
            {"$set": {"floors": block['floors']}}
        )

        if result.modified_count == 0:
            return {"success": False, "message": "No changes made"}, 400

        return {"success": True, "message": "Floor layout copied successfully"}
    except Exception as e:
        return {"success": False, "message": f"Error copying floor layout: {str(e)}"}, 500

@admin_bp.route("/get_rooms/<block_id>/<int:floor_index>", methods=["GET"])
@login_required
def get_rooms(block_id, floor_index):
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    block = db.blocks.find_one({"_id": ObjectId(block_id)})
    if not block or floor_index >= len(block["floors"]):
        return {"success": False, "message": "Block or floor not found"}, 404

    floor = block["floors"][floor_index]
    rooms = []
    for room_type in ["single", "double", "triple"]:
        rooms.extend([{"number": num, "type": room_type} for num in floor[f"{room_type}NonAttachedRoomNumbers"]])
        rooms.extend([{"number": num, "type": f"{room_type}_attached"} for num in floor[f"{room_type}AttachedRoomNumbers"]])

    return jsonify({"success": True, "rooms": rooms})

@admin_bp.route("/get_unassigned_students", methods=["GET"])
@login_required
def get_unassigned_students():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    unassigned_students = list(users.find(
        {"role": "student", "room_assignment": {"$exists": False}},
        {"_id": 1, "username": 1, "full_name": 1}
    ))
    
    # Convert ObjectId to string for JSON serialization
    for student in unassigned_students:
        student['_id'] = str(student['_id'])
    
    return jsonify({"success": True, "students": unassigned_students})

@admin_bp.route("/assign_room", methods=["POST"])
@login_required
def assign_room():
    print("Entering assign_room function")
    if session["user"]["role"] != "admin":
        print("Unauthorized access attempt")
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        print("Received data:", data)

        block_id = data.get("blockId")
        floor_index = data.get("floorIndex")
        room_number = data.get("roomNumber")
        student_id = data.get("studentId")
        room_type = data.get("roomType")
        is_attached = data.get("isAttached")

        print(f"Parsed data: block_id={block_id}, floor_index={floor_index}, room_number={room_number}, student_id={student_id}, room_type={room_type}, is_attached={is_attached}")

        # Validate input
        if not all([block_id, floor_index is not None, room_number, student_id, room_type, is_attached is not None]):
            print("Missing required fields")
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # Convert floor_index to int
        try:
            floor_index = int(floor_index)
        except ValueError:
            print("Invalid floor index")
            return jsonify({"success": False, "message": "Invalid floor index"}), 400

        # Convert block_id and student_id to ObjectId
        try:
            block_id = ObjectId(block_id)
            student_id = ObjectId(student_id)
        except bson_errors.InvalidId as e:
            print(f"Invalid ObjectId: {str(e)}")
            return jsonify({"success": False, "message": f"Invalid block or student ID: {str(e)}"}), 400

        print("Querying block")
        block = db.blocks.find_one({"_id": block_id})
        if not block or floor_index >= len(block["floors"]):
            print("Block or floor not found")
            return jsonify({"success": False, "message": "Block or floor not found"}), 404

        print("Querying student")
        student = users.find_one({"_id": student_id, "role": "student"})
        if not student:
            print("Student not found")
            return jsonify({"success": False, "message": "Student not found"}), 404

        print("Checking existing assignments")
        existing_assignments = db.room_assignments.count_documents({
            "block_id": str(block_id),
            "floor_index": floor_index,
            "room_number": room_number
        })
        
        room_capacity = 1 if room_type == "single" else (2 if room_type == "double" else 3)
        if existing_assignments >= room_capacity:
            print("Room is already full")
            return jsonify({"success": False, "message": "Room is already full"}), 400

        print("Creating assignment")
        assignment = {
            "block_id": str(block_id),
            "block_name": block["name"],
            "floor_index": floor_index,
            "room_number": room_number,
            "room_type": room_type,
            "is_attached": is_attached,
            "student_id": str(student_id),
            "student_name": student["full_name"]
        }

        print("Inserting assignment")
        result = db.room_assignments.insert_one(assignment)
        print("Updating user")
        users.update_one({"_id": student_id}, {"$set": {"room_assignment": str(result.inserted_id)}})

        print("Assignment successful")
        return jsonify({"success": True, "message": "Room assigned successfully"})

    except Exception as e:
        print("Error in assign_room:", str(e))
        print(traceback.format_exc())
        return jsonify({"success": False, "message": f"Error assigning room: {str(e)}"}), 500

@admin_bp.route("/get_room_assignments", methods=["GET"])
@login_required
def get_room_assignments():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    assignments = list(db.room_assignments.find({}, {"_id": {"$toString": "$_id"}}))
    return jsonify({"success": True, "assignments": assignments})

@admin_bp.route("/get_all_room_assignments", methods=["GET"])
@login_required
def get_all_room_assignments():
    if session["user"]["role"] != "admin":
        return {"success": False, "message": "Unauthorized"}, 403

    assignments = list(db.room_assignments.find())
    for assignment in assignments:
        assignment["_id"] = str(assignment["_id"])
        assignment["capacity"] = 1 if assignment["room_type"] == "single" else (2 if assignment["room_type"] == "double" else 3)
        assignment["occupants"] = db.room_assignments.count_documents({
            "block_id": assignment["block_id"],
            "floor_index": assignment["floor_index"],
            "room_number": assignment["room_number"]
        })
    return jsonify({"success": True, "assignments": assignments})

@admin_bp.route('/unassign_room/<assignment_id>', methods=['POST'])
@login_required
def unassign_room(assignment_id):
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        assignment = room_assignments.find_one_and_delete({"_id": ObjectId(assignment_id)})
        if assignment:
            # Update the student's room assignment
            if "student_id" in assignment:
                users.update_one(
                    {"_id": ObjectId(assignment["student_id"])},
                    {"$unset": {"room_assignment": ""}}
                )
            
            return jsonify({"success": True, "message": "Room unassigned successfully"})
        else:
            return jsonify({"success": False, "message": "Assignment not found"})
    except Exception as e:
        print(f"Error in unassign_room: {str(e)}")
        return jsonify({"success": False, "message": f"An error occurred: {str(e)}"})
    
    
@admin_bp.route("/get_block/<block_id>", methods=["GET"])
@login_required
def get_block(block_id):
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        block = db.blocks.find_one({"_id": ObjectId(block_id)})
        if block:
            block['_id'] = str(block['_id'])  # Convert ObjectId to string
            return jsonify({"success": True, "block": block})
        else:
            return jsonify({"success": False, "message": "Block not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Error retrieving block: {str(e)}"}), 500

@admin_bp.route("/update_block", methods=["POST"])
@login_required
def update_block():
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        data = request.json
        block_id = data.get('blockId')
        block_name = data.get('blockName')
        floors = data.get('floors')

        if not all([block_id, block_name, floors]):
            return jsonify({"success": False, "message": "Missing required fields"}), 400

        # Validate and process floor data
        for floor in floors:
            for room_type in ['single', 'double', 'triple']:
                total_rooms = int(floor[f"{room_type}Rooms"])
                attached_rooms = floor[f"{room_type}AttachedRoomNumbers"].split(',') if floor[f"{room_type}AttachedRoomNumbers"] else []
                non_attached_rooms = floor[f"{room_type}NonAttachedRoomNumbers"].split(',') if floor[f"{room_type}NonAttachedRoomNumbers"] else []
                
                attached_rooms = [room.strip() for room in attached_rooms if room.strip()]
                non_attached_rooms = [room.strip() for room in non_attached_rooms if room.strip()]
                
                if len(attached_rooms) + len(non_attached_rooms) != total_rooms:
                    return jsonify({"success": False, "message": f"Total {room_type} rooms does not match the number of room numbers provided"}), 400

                floor[f"{room_type}AttachedRoomNumbers"] = attached_rooms
                floor[f"{room_type}NonAttachedRoomNumbers"] = non_attached_rooms

        result = db.blocks.update_one(
            {"_id": ObjectId(block_id)},
            {"$set": {
                "name": block_name,
                "floors": floors
            }}
        )

        if result.modified_count > 0:
            return jsonify({"success": True, "message": "Block updated successfully"})
        else:
            return jsonify({"success": False, "message": "No changes made or block not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Error updating block: {str(e)}"}), 500


@admin_bp.route("/delete_block/<block_id>", methods=["POST"])
@login_required
def delete_block(block_id):
    if session["user"]["role"] != "admin":
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    try:
        result = db.blocks.delete_one({"_id": ObjectId(block_id)})
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Block deleted successfully"})
        else:
            return jsonify({"success": False, "message": "Block not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Error deleting block: {str(e)}"}), 500