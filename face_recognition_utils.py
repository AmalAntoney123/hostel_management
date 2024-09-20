import face_recognition
import numpy as np
from io import BytesIO
from PIL import Image
import base64

def process_face_image(image_data):
    try:
        # Decode base64 image data
        image_data = base64.b64decode(image_data.split(',')[1])
        image = Image.open(BytesIO(image_data))
        
        # Convert image to RGB (in case it's not)
        image = image.convert('RGB')
        
        # Convert PIL Image to numpy array
        image_array = np.array(image)
        
        # Find face locations in the image
        face_locations = face_recognition.face_locations(image_array)
        
        if len(face_locations) == 0:
            return None
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(image_array, face_locations)
        
        if len(face_encodings) == 0:
            return None
        
        # Return the first face encoding
        return face_encodings[0]
    except Exception as e:
        print(f"Error processing face image: {str(e)}")
        return None

def recognize_face(image_data, known_face_encodings):
    try:
        # Process the captured image
        face_encoding = process_face_image(image_data)
        
        if face_encoding is None:
            return None
        
        # Compare the face encoding with known face encodings
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        
        if True in matches:
            return matches.index(True)
        else:
            return None
    except Exception as e:
        print(f"Error recognizing face: {str(e)}")
        return None