# Hostel Management System

A comprehensive web-based solution for managing hostel operations efficiently, featuring an advanced Face Recognition Attendance System.

## 🌟 Features

- User authentication and role-based access control
- Room assignment and management
- Complaint handling system
- Inventory management
- Gatepass system
- Fee management
- Notice board
- Face Recognition Attendance System

## 🚀 Getting Started

### Prerequisites

- Python 3.7+
- MongoDB
- pip
- OpenCV
- dlib

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/amalantoney123/hostel-management-system.git
   cd hostel-management-system
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the root directory and add the following:
   ```
   MONGODB_URI=your_mongodb_connection_string
   SECRET_KEY=your_secret_key
   ```

5. Run the application:
   ```
   python app.py
   ```

## 🛠️ Technology Stack

- Backend: Flask (Python)
- Database: MongoDB
- Frontend: HTML, CSS, JavaScript
- CSS Framework: Bootstrap
- Face Recognition: OpenCV, dlib

## 🔒 Security

This project implements various security measures, including:

- Password hashing
- CSRF protection
- Secure session management
- Encrypted face data storage

## 📷 Face Recognition Attendance System

Our state-of-the-art Face Recognition Attendance System provides:

- Automated attendance tracking
- Real-time face detection and recognition
- Integration with the hostel management database
- Attendance reports and analytics

To set up the Face Recognition system:

1. Ensure OpenCV and dlib are properly installed
2. Add student/resident photos to the `face_data` directory
3. Run the face encoding script:
   ```
   python generate_face_encodings.py
   ```
4. The attendance system will automatically start with the main application

## 📚 API Documentation

For detailed API documentation, please refer to the `api_docs.md` file in the repository.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## 📞 Contact

If you have any questions, feel free to reach out to us at [amalantoney123@gmail.com](mailto:amalantoney123@gmail.com).
