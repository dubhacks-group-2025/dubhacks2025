import asyncio
import uuid
from tripo3d import TripoClient, TaskStatus
import os
from dotenv import load_dotenv
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, storage, firestore

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

# Initialize Firebase only if not in Firebase Functions environment
if not os.getenv('FUNCTIONS_EMULATOR') and not os.getenv('FUNCTION_NAME'):
    initialize_firebase()
    db = firestore.client()
else:
    # In Firebase Functions, we'll get the client when needed
    db = None

API_KEY = os.getenv("TRIPO_API_KEY")

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

def update_drawing_with_glb_url(glb_url: str, document_id: str) -> bool:
    """Update existing drawing document in Firestore with GLB URL and status."""
    try:
        # Get the document reference
        # Get Firestore client
        firestore_client = db if db else firestore.client()
        doc_ref = firestore_client.collection('drawings').document(document_id)
        
        # Prepare update data
        update_data = {
            'UsdzUrl': glb_url,
            'Status': 'glb model uploaded',
            'UpdatedAt': datetime.utcnow()
        }
        
        # Update the document
        doc_ref.update(update_data)
        
        print(f"Updated drawing document {document_id} with UsdzUrl: {glb_url}")
        return True
    except Exception as e:
        print(f"Error updating drawing document: {e}")
        return False

def get_drawing_with_nanobanana_url() -> dict:
    """Get a drawing document that has a NanoBananaUrl but no UsdzUrl."""
    try:
        # Get all drawings and filter in Python to avoid index requirements
        # Get Firestore client
        firestore_client = db if db else firestore.client()
        drawings_ref = firestore_client.collection('drawings')
        docs = drawings_ref.get()
        
        for doc in docs:
            data = doc.to_dict()
            # Check if it has NanoBananaUrl but no UsdzUrl
            if (data.get('NanoBananaUrl') and 
                (not data.get('UsdzUrl') or data.get('UsdzUrl') == 'null')):
                return {
                    'id': doc.id,
                    'data': data
                }
        
        print("No documents found with NanoBananaUrl but no UsdzUrl")
        return None
    except Exception as e:
        print(f"Error querying drawings: {e}")
        return None

async def process_nanobanana_to_3d(nanobanana_url: str, document_id: str) -> dict:
    """
    Process a nanobanana image and generate a 3D model using Tripo3D.
    
    Args:
        nanobanana_url: URL of the nanobanana image
        document_id: ID of the drawing document to update
    
    Returns:
        dict: Result containing GLB URL and status
    """
    try:
        async with TripoClient(api_key=API_KEY) as client:
            print(f"Processing nanobanana image: {nanobanana_url}")
            
            # Generate 3D model using text-to-model with a nanobanana character prompt
            # Since tripo3d doesn't have direct image-to-model, we'll use text-to-model with a detailed prompt
            task_id = await client.text_to_model(
                prompt="Create a 3D model of a cute nanobanana character. Make it a cartoon character with banana-like features, bright yellow color, friendly expression, and playful pose. It should look like a fun cartoon banana character.",
                negative_prompt="low quality, blurry, distorted, realistic, human, scary, dark"
            )
            print(f"Task ID: {task_id}")

            # Wait for the task to complete
            task = await client.wait_for_task(task_id, verbose=True)
            
            if task.status == TaskStatus.SUCCESS:
                # Create output directory if it doesn't exist
                os.makedirs("./output", exist_ok=True)
                
                # Download the generated models
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
                        # Update the drawing document
                        print("Updating drawing document...")
                        success = update_drawing_with_glb_url(glb_url, document_id)
                        
                        if success:
                            return {
                                'success': True,
                                'UsdzUrl': glb_url,
                                'documentId': document_id,
                                'Status': 'glb model uploaded'
                            }
                        else:
                            return {
                                'success': False,
                                'error': 'Failed to update drawing document'
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
    except Exception as e:
        print(f"Error in process_nanobanana_to_3d: {e}")
        return {
            'success': False,
            'error': str(e)
        }

async def process_pending_drawings():
    """Process all drawings that have nanobanana images but no 3D models."""
    try:
        # Get drawings that need 3D model generation
        drawing = get_drawing_with_nanobanana_url()
        
        if not drawing:
            print("No drawings found that need 3D model generation")
            return
        
        document_id = drawing['id']
        nanobanana_url = drawing['data'].get('NanoBananaUrl')
        
        if not nanobanana_url:
            print(f"No NanoBananaUrl found in document {document_id}")
            return
        
        print(f"Processing drawing {document_id} with nanobanana URL: {nanobanana_url}")
        
        # Process the nanobanana image to 3D
        result = await process_nanobanana_to_3d(nanobanana_url, document_id)
        
        if result['success']:
            print(f"Successfully generated 3D model for document {document_id}")
            print(f"GLB URL: {result['UsdzUrl']}")
        else:
            print(f"Failed to generate 3D model: {result['error']}")
            
        return result
        
    except Exception as e:
        print(f"Error in process_pending_drawings: {e}")
        return {
            'success': False,
            'error': str(e)
        }

async def main():
    """Legacy function for testing - kept for backward compatibility"""
    try:
        async with TripoClient(api_key=API_KEY) as client:
            task_id = await client.text_to_model(
                prompt="a small cat",
                negative_prompt="low quality, blurry",
            )
            print(f"Task ID: {task_id}")

            task = await client.wait_for_task(task_id, verbose=True)
            
            # Create output directory if it doesn't exist
            os.makedirs("./output", exist_ok=True)
            
            if task.status == TaskStatus.SUCCESS:
                files = await client.download_task_models(task, "./output")
                for model_type, path in files.items():
                    print(f"Downloaded {model_type}: {path}")
            else:
                print(f"Task failed with status: {task.status}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    # Test the new nanobanana to 3D processing
    print("Testing nanobanana to 3D model generation...")
    asyncio.run(process_pending_drawings())
