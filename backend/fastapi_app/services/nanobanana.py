import os
import uuid
from io import BytesIO
from PIL import Image
import requests
from dotenv import load_dotenv
from datetime import datetime

from google import genai  # pip install google-genai
from google.genai import types
import firebase_admin
from firebase_admin import credentials, storage, firestore

from datetime import timedelta
from fastapi import APIRouter, HTTPException

# Load environment variables from .env file
load_dotenv()

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    try:
        # Check if Firebase is already initialized
        firebase_admin.get_app()
        print("Firebase already initialized")
    except ValueError:
        # Initialize Firebase
        cred = credentials.Certificate('/Users/kellie/dubhacks-2025/dubhacks2025-26629-firebase-adminsdk-fbsvc-314f3d937f.json')
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'dubhacks2025-26629.firebasestorage.app'
        })
        print("Firebase initialized successfully")

# Initialize Firebase
initialize_firebase()
db = firestore.client()

# Initialize Google GenAI client
api_key = os.getenv("GEMINI_API_KEY")
try:
    client = genai.Client(api_key=api_key)
    print("Google GenAI client initialized successfully")
except Exception as e:
    print(f"Error initializing Google GenAI client: {e}")
    client = None

#def get_image_from_firebase_storage(image_path: str) -> Image.Image:
"""Download image from Firebase Storage using Admin SDK.
try:
    bucket = storage.bucket()
    blob = bucket.blob(image_path)
    
    # Check if the blob exists
    if not blob.exists():
        print(f"Image '{image_path}' not found in Firebase Storage")
        return None
    
    # Download the image content as bytes
    image_data = blob.download_as_bytes()
    
    # Convert to PIL Image
    return Image.open(BytesIO(image_data))
except Exception as e:
    print(f"Error downloading image from Firebase Storage: {e}")
    return None
"""

def url_to_image(url: str) -> Image.Image:
    """Download image from URL and return PIL Image object."""
    # Add https:// if the URL doesn't have a scheme
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))

def upload_image_to_firebase_storage(image: Image.Image, filename: str) -> str:
    """Upload PIL Image to Firebase Storage and return the download URL."""
    try:
        bucket = storage.bucket()
        
        # Convert PIL Image to bytes
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Create blob and upload
        blob = bucket.blob(f"generated_images/{filename}")
        blob.upload_from_string(img_byte_arr, content_type='image/png')
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Return the public URL
        return blob.public_url
    except Exception as e:
        print(f"Error uploading image to Firebase Storage: {e}")
        return None

def update_drawing_document(image_url: str, original_image_url: str, prompt: str, user_id: str = None) -> str:
    """Update existing drawing document in Firestore with generated image URL and status."""
    try:
        # Find the document that matches the original image URL
        drawings_ref = db.collection('drawings')
        query = drawings_ref.where('OriginalImageUrl', '==', original_image_url)
        docs = query.get()
        
        if not docs:
            print(f"No document found with OriginalImageUrl: {original_image_url}")
            return None
        
        # Update the first matching document
        doc = docs[0]
        doc_ref = doc.reference
        
        # Prepare update data
        update_data = {
            'NanoBananaUrl': image_url,
            'Status': 'nano banana image generated',
            'UpdatedAt': datetime.utcnow()
        }
        
        # Add Text_Prompt if it's provided and not empty
        if prompt and prompt.strip():
            update_data['Text_Prompt'] = prompt
        
        # Update the document
        doc_ref.update(update_data)
        
        print(f"Updated drawing document {doc.id} with NanoBananaUrl: {image_url}")
        return doc.id
    except Exception as e:
        print(f"Error updating drawing document: {e}")
        return None

def get_item_from_firestore(collection_name: str='drawings', document_id: str='2iYllCFtF5yQqWMOaHRs', attribute_name: str='OriginalImageUrl') -> str:
    
    doc_ref = db.collection(collection_name).document(document_id)
    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict()
        
        if attribute_name in data:
            attribute_value = data[attribute_name]
            print(f"The value of '{attribute_name}' is: {attribute_value}")
            return attribute_value
        else:
            print(f"Attribute '{attribute_name}' not found in document.")
            return None
    else:
        print(f"No such document: {document_id}")
        return None


def process_uploaded_image(original_image_url: str, prompt: str, user_id: str = None) -> dict:
    """
    Main function to process uploaded image and generate nanobanana version.
    This function can be called by Firebase Cloud Functions.
    
    Args:
        original_image_url: URL of the uploaded image
        prompt: Text prompt for image generation
        user_id: Optional user ID
    
    Returns:
        dict: Result containing generated image URL and document ID
    """
    try:
        # Check if client is available
        if client is None:
            return {
                'success': False,
                'error': 'Google GenAI client not available. Please check your API key.'
            }
        
        # Download the original image
        print(f"Processing image from URL: {original_image_url}")
        original_image = url_to_image(original_image_url)
        
        # Generate content using Gemini
        print(f"Generating content with prompt: {prompt}")
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt, original_image],
        )
        
        # Process the response
        generated_image = None
        generated_text = ""
        
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                generated_text = part.text
                print(f"Generated text: {generated_text}")
            elif part.inline_data is not None:
                generated_image = Image.open(BytesIO(part.inline_data.data))
                print("Generated image received")
        
        if generated_image is None:
            return {
                'success': False,
                'error': 'No image was generated from the prompt'
            }
        
        # Generate unique filename
        filename = f"nanobanana_{uuid.uuid4()}.png"
        
        # Upload generated image to Firebase Storage
        print("Uploading generated image to Firebase Storage...")
        generated_image_url = upload_image_to_firebase_storage(generated_image, filename)
        
        if generated_image_url is None:
            return {
                'success': False,
                'error': 'Failed to upload image to Firebase Storage'
            }
        
        # Update existing drawing document in Firestore
        print("Updating drawing document in Firestore...")
        doc_id = update_drawing_document(
            generated_image_url, 
            original_image_url, 
            prompt, 
            user_id
        )
        
        if doc_id is None:
            return {
                'success': False,
                'error': 'Failed to update drawing document in Firestore'
            }
        
        return {
            'success': True,
            'NanoBananaUrl': generated_image_url,
            'OriginalImageUrl': original_image_url,
            'Text_Prompt': prompt,
            'generatedText': generated_text,
            'documentId': doc_id,
            'UserId': user_id,
            'Status': 'nano banana image generated'
        }
        
    except Exception as e:
        print(f"Error in process_uploaded_image: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def generate_image(prompt: str, out_path: str) -> list[Image.Image]:
    """Legacy function for testing - kept for backward compatibility"""
    # Try to get the image from Firebase Storage first
    #image = get_image_from_firebase_storage('Profile_Photo_Tennis.JPG')
    
    # If image not found in Firebase Storage, try to get it from Firestore URL
    
    
    try:
        image_url = get_item_from_firestore(attribute_name='OriginalImageUrl')
        if image_url:
            image = url_to_image(image_url)
            print(f"Successfully loaded image from URL: {image_url}")
        else:
            print("No image URL found in Firestore")
    except Exception as e:
        print(f"Error getting image from Firestore: {e}")
    
    # Check if client is available
    if client is None:
        print("Google GenAI client not available. Please check your API key.")
        return []
    
    # If still no image, create a simple placeholder or skip image generation
    if image is None:
        print("No image available, generating text-only response...")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
            )
        except Exception as e:
            print(f"Error generating content: {e}")
            return []
    else:
        # Save the loaded image
        image.save("nanobanana_sample.png")
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt, image],
            )
        except Exception as e:
            print(f"Error generating content: {e}")
            return []

    try:
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                generated_image = Image.open(BytesIO(part.inline_data.data))
                generated_image.save("generated_image.png")
    except Exception as e:
        print(f"Error processing response: {e}")
        return []



if __name__ == "__main__":
    # Example usage - test the new cloud function
    example_prompt = (
        "A cartoon character playing tennis "
        "with a ping pong paddle and a tennis ball"
    )
    
    # Get the original image URL from Firestore
    original_image_url = get_item_from_firestore(attribute_name='OriginalImageUrl')
    
    if original_image_url:
        print(f"Testing with original image: {original_image_url}")
        
        # Test the new process_uploaded_image function
        result = process_uploaded_image(
            original_image_url=original_image_url,
            prompt=example_prompt,
            user_id="test_user_123"
        )
        
        print("Result:", result)
    else:
        print("No original image URL found, testing legacy function...")
        generate_image(example_prompt, out_path="generated_image.png")
