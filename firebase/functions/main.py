import os
import sys
import asyncio
import uuid
from firebase_functions import firestore_fn, https_fn
from firebase_admin import initialize_app, firestore, storage
from datetime import datetime
from io import BytesIO
from PIL import Image
import requests
from google import genai
from tripo3d import TripoClient, TaskStatus

from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase Admin SDK (only if not already initialized)
try:
    initialize_app()
except ValueError as e:
    if "already exists" in str(e):
        print("Firebase app already initialized")
    else:
        raise e

# Initialize Google GenAI client
# Hardcode API keys for now to test
api_key = "AIzaSyA22_1EhLMyMtl7DUySbYIxj-fgMnnKai0"  # Your Gemini API key
tripo_api_key = "tsk_1cG6gsYSvQkstYycrQKo0kQWW5jjHLkh_3vPrbQlCZf"  # Your Tripo API key

try:
    genai_client = genai.Client(api_key=api_key)
    print("Google GenAI client initialized successfully")
except Exception as e:
    print(f"Error initializing Google GenAI client: {e}")
    genai_client = None

print(f"Tripo API key available: {bool(tripo_api_key)}")

def url_to_image(url: str) -> Image.Image:
    """Download image from URL and return PIL Image object."""
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

def upload_glb_to_firebase_storage(glb_file_path: str, filename: str) -> str:
    """Upload GLB file to Firebase Storage and return the download URL."""
    try:
        bucket = storage.bucket()
        
        # Create blob and upload
        blob = bucket.blob(f"3d_models/{filename}")
        blob.upload_from_filename(glb_file_path, content_type='model/gltf-binary')
        
        # Make the blob publicly accessible
        blob.make_public()
        
        # Return the public URL
        return blob.public_url
    except Exception as e:
        print(f"Error uploading GLB to Firebase Storage: {e}")
        return None

def process_uploaded_image(original_image_url: str, prompt: str, user_id: str = None) -> dict:
    """Process uploaded image and generate nanobanana version."""
    try:
        if genai_client is None:
            return {
                'success': False,
                'error': 'Google GenAI client not available. Please check your API key.'
            }
        
        # Download the original image
        print(f"Processing image from URL: {original_image_url}")
        original_image = url_to_image(original_image_url)
        
        # Generate content using Gemini
        print(f"Generating content with prompt: {prompt}")
        response = genai_client.models.generate_content(
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
        
        return {
            'success': True,
            'NanoBananaUrl': generated_image_url,
            'OriginalImageUrl': original_image_url,
            'Text_Prompt': prompt,
            'generatedText': generated_text,
            'UserId': user_id,
            'Status': 'nano banana image generated'
        }
        
    except Exception as e:
        print(f"Error in process_uploaded_image: {e}")
        return {
            'success': False,
            'error': str(e)
        }

async def process_nanobanana_to_3d(nanobanana_url: str, document_id: str) -> dict:
    """Process a nanobanana image and generate a 3D model using Tripo3D."""
    try:
        if not tripo_api_key:
            return {
                'success': False,
                'error': 'TRIPO_API_KEY not available'
            }
        
        print(f"Starting 3D model generation for document {document_id}")
        
        async with TripoClient(api_key=tripo_api_key) as client:
            print(f"Processing nanobanana image: {nanobanana_url}")
            
            # Generate 3D model using text-to-model
            task_id = await client.text_to_model(
                prompt="Create a 3D model of a cute nanobanana character. Make it a cartoon character with banana-like features, bright yellow color, friendly expression, and playful pose. It should look like a fun cartoon banana character.",
                negative_prompt="low quality, blurry, distorted, realistic, human, scary, dark"
            )
            print(f"Task ID: {task_id}")

            # Wait for the task to complete with a shorter timeout
            print("Waiting for 3D model generation to complete...")
            task = await asyncio.wait_for(
                client.wait_for_task(task_id, verbose=True),
                timeout=240  # 4 minutes timeout
            )
            
            print(f"Task completed with status: {task.status}")
            
            if task.status == TaskStatus.SUCCESS:
                # Create output directory if it doesn't exist
                os.makedirs("./output", exist_ok=True)
                
                # Download the generated models
                print("Downloading generated models...")
                files = await client.download_task_models(task, "./output")
                
                # Find the GLB file
                glb_file_path = None
                for model_type, path in files.items():
                    print(f"Downloaded {model_type}: {path}")
                    if path.endswith('.glb'):
                        glb_file_path = path
                        break
                
                if glb_file_path:
                    # Generate unique filename
                    filename = f"nanobanana_3d_{uuid.uuid4()}.glb"
                    
                    # Upload GLB to Firebase Storage
                    print("Uploading GLB to Firebase Storage...")
                    glb_url = upload_glb_to_firebase_storage(glb_file_path, filename)
                    
                    if glb_url:
                        print(f"Successfully uploaded GLB: {glb_url}")
                        return {
                            'success': True,
                            'UsdzUrl': glb_url,
                            'documentId': document_id,
                            'Status': 'glb model uploaded'
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'Failed to upload GLB to Firebase Storage'
                        }
                else:
                    return {
                        'success': False,
                        'error': 'No GLB file found in generated models'
                    }
            else:
                return {
                    'success': False,
                    'error': f'Task failed with status: {task.status}'
                }
    except asyncio.TimeoutError:
        print(f"3D model generation timed out for document {document_id}")
        return {
            'success': False,
            'error': '3D model generation timed out'
        }
    except Exception as e:
        print(f"Error in process_nanobanana_to_3d: {e}")
        return {
            'success': False,
            'error': str(e)
        }

@firestore_fn.on_document_created(document="drawings/{docId}")
def process_new_drawing(event: firestore_fn.Event[firestore_fn.DocumentSnapshot | None]) -> None:
    """
    Cloud Function triggered when a new document is created in the 'drawings' collection.
    This function processes the uploaded image through the complete pipeline:
    1. Generate nanobanana version using the original image and text prompt
    2. Upload nanobanana image to storage and update NanoBananaUrl field
    3. Generate 3D model using Tripo3D
    4. Upload GLB file to 3d_models folder and update UsdzUrl field
    """
    try:
        if event.data is None:
            print("No document data received")
            return
        
        # Get the document data
        doc_data = event.data.to_dict()
        doc_id = event.data.id
        
        print(f"Processing new drawing document: {doc_id}")
        print(f"Document data: {doc_data}")
        
        # Extract required fields
        original_image_url = doc_data.get('OriginalImageUrl')
        text_prompt = doc_data.get('Text_Prompt', '')
        user_id = doc_data.get('UserId', 'unknown')
        
        # Validate required fields
        if not original_image_url:
            print(f"No OriginalImageUrl found in document {doc_id}")
            return
        
        # Update status to processing
        update_document_status(doc_id, 'processing', 'Starting image processing...')
        
        # Step 1: Generate nanobanana version
        print(f"Step 1: Generating nanobanana version for document {doc_id}")
        nanobanana_result = process_uploaded_image(
            original_image_url=original_image_url,
            prompt=text_prompt or "Transform this image into a cartoon nanobanana character while keeping the main subject recognizable",
            user_id=user_id
        )
        
        if not nanobanana_result['success']:
            print(f"Failed to generate nanobanana image: {nanobanana_result['error']}")
            update_document_status(doc_id, 'error', f"Nanobanana generation failed: {nanobanana_result['error']}")
            return
        
        nanobanana_url = nanobanana_result['NanoBananaUrl']
        print(f"Successfully generated nanobanana image: {nanobanana_url}")
        
        # Update document with nanobanana URL
        update_document_with_nanobanana(doc_id, nanobanana_url)
        update_document_status(doc_id, 'nanobanana_completed', 'Nanobanana image generated successfully')
        
        # Step 2: Generate 3D model using Tripo3D
        print(f"Step 2: Generating 3D model for document {doc_id}")
        update_document_status(doc_id, 'generating_3d', 'Generating 3D model...')
        
        # Run the async 3D generation with timeout
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Set a longer timeout for 3D model generation (5 minutes)
            tripo_result = loop.run_until_complete(
                asyncio.wait_for(
                    process_nanobanana_to_3d(nanobanana_url, doc_id),
                    timeout=300  # 5 minutes timeout
                )
            )
        except asyncio.TimeoutError:
            print(f"3D model generation timed out for document {doc_id}")
            update_document_status(doc_id, 'error', '3D model generation timed out')
            return
        except Exception as e:
            print(f"Error in 3D generation: {e}")
            update_document_status(doc_id, 'error', f'3D model generation failed: {str(e)}')
            return
        finally:
            loop.close()
        
        if not tripo_result['success']:
            print(f"Failed to generate 3D model: {tripo_result['error']}")
            update_document_status(doc_id, 'error', f"3D model generation failed: {tripo_result['error']}")
            return
        
        usdz_url = tripo_result['UsdzUrl']
        print(f"Successfully generated 3D model: {usdz_url}")
        
        # Update document with 3D model URL
        update_document_with_3d_model(doc_id, usdz_url)
        update_document_status(doc_id, 'completed', 'All processing completed successfully')
        
        print(f"Successfully completed processing for document {doc_id}")
        
    except Exception as e:
        print(f"Error in process_new_drawing: {e}")
        if event.data:
            update_document_status(event.data.id, 'error', f"Processing failed: {str(e)}")

def update_document_status(doc_id: str, status: str, message: str = None):
    """Update the status field of a document in the drawings collection."""
    try:
        db = firestore.client()
        doc_ref = db.collection('drawings').document(doc_id)
        
        update_data = {
            'Status': status,
            'UpdatedAt': datetime.utcnow()
        }
        
        if message:
            update_data['StatusMessage'] = message
        
        doc_ref.update(update_data)
        print(f"Updated document {doc_id} status to: {status}")
        
    except Exception as e:
        print(f"Error updating document status: {e}")

def update_document_with_nanobanana(doc_id: str, nanobanana_url: str):
    """Update the document with the nanobanana image URL."""
    try:
        db = firestore.client()
        doc_ref = db.collection('drawings').document(doc_id)
        
        doc_ref.update({
            'NanoBananaUrl': nanobanana_url,
            'UpdatedAt': datetime.utcnow()
        })
        print(f"Updated document {doc_id} with NanoBananaUrl: {nanobanana_url}")
        
    except Exception as e:
        print(f"Error updating document with nanobanana URL: {e}")

def update_document_with_3d_model(doc_id: str, usdz_url: str):
    """Update the document with the 3D model URL."""
    try:
        db = firestore.client()
        doc_ref = db.collection('drawings').document(doc_id)
        
        doc_ref.update({
            'UsdzUrl': usdz_url,
            'UpdatedAt': datetime.utcnow()
        })
        print(f"Updated document {doc_id} with UsdzUrl: {usdz_url}")
        
    except Exception as e:
        print(f"Error updating document with 3D model URL: {e}")

@https_fn.on_request()
def process_drawing_manual(req: https_fn.Request) -> https_fn.Response:
    """
    Manual HTTP trigger to process a specific drawing document.
    POST request body should contain:
    {
        "docId": "document_id_here"
    }
    """
    try:
        # Handle CORS
        if req.method == 'OPTIONS':
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            }
            return https_fn.Response('', 204, headers)
        
        if req.method != 'POST':
            return https_fn.Response('Method not allowed', 405)
        
        # Parse request data
        data = req.get_json()
        if not data:
            return https_fn.Response('No JSON data provided', 400)
        
        doc_id = data.get('docId')
        if not doc_id:
            return https_fn.Response('docId is required', 400)
        
        # Get the document
        db = firestore.client()
        doc_ref = db.collection('drawings').document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return https_fn.Response('Document not found', 404)
        
        # Create a mock event to trigger the processing
        class MockEvent:
            def __init__(self, doc_id, doc_data):
                self.data = MockDocumentSnapshot(doc_id, doc_data)
        
        class MockDocumentSnapshot:
            def __init__(self, doc_id, doc_data):
                self.id = doc_id
                self._data = doc_data
            
            def to_dict(self):
                return self._data
        
        # Trigger the processing function
        mock_event = MockEvent(doc_id, doc.to_dict())
        process_new_drawing(mock_event)
        
        # Return success response
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
        }
        return https_fn.Response('{"status": "processing_started"}', 200, headers)
        
    except Exception as e:
        print(f"Error in process_drawing_manual: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
        }
        return https_fn.Response(f'{{"error": "{str(e)}"}}', 500, headers)

@https_fn.on_request()
def get_drawing_status(req: https_fn.Request) -> https_fn.Response:
    """
    Get the status of a drawing document.
    GET request with query parameter: ?docId=document_id_here
    """
    try:
        # Handle CORS
        if req.method == 'OPTIONS':
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
            }
            return https_fn.Response('', 204, headers)
        
        if req.method != 'GET':
            return https_fn.Response('Method not allowed', 405)
        
        doc_id = req.args.get('docId')
        if not doc_id:
            return https_fn.Response('docId query parameter is required', 400)
        
        # Get the document
        db = firestore.client()
        doc_ref = db.collection('drawings').document(doc_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return https_fn.Response('Document not found', 404)
        
        doc_data = doc.to_dict()
        
        # Return document data
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
        }
        
        import json
        return https_fn.Response(json.dumps(doc_data, default=str), 200, headers)
        
    except Exception as e:
        print(f"Error in get_drawing_status: {e}")
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
        }
        return https_fn.Response(f'{{"error": "{str(e)}"}}', 500, headers)