#!/usr/bin/env python3
"""
Manual script to process a stuck document
"""
import asyncio
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import process_nanobanana_to_3d, update_document_status

async def manual_process():
    # Document ID that got stuck
    doc_id = "YOUR_DOCUMENT_ID_HERE"  # Replace with actual document ID
    nanobanana_url = "https://storage.googleapis.com/dubhacks2025-26629.firebasestorage.app/generated_images/nanobanana_de9ea5d1-72b6-4057-a2c2-166db4caa359.png"
    
    print(f"Processing document {doc_id} with nanobanana URL: {nanobanana_url}")
    
    try:
        result = await process_nanobanana_to_3d(nanobanana_url, doc_id)
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(manual_process())


