#!/usr/bin/env python3
"""
Script to update Firebase Functions timeout to 9 minutes (540 seconds)
"""
import subprocess
import sys

def update_function_timeout():
    try:
        # Update the function timeout to 9 minutes (540 seconds)
        cmd = [
            "gcloud", "functions", "deploy", "process_new_drawing",
            "--runtime", "python313",
            "--trigger-event", "providers/cloud.firestore/eventTypes/document.create",
            "--trigger-resource", "projects/dubhacks2025-26629/databases/(default)/documents/drawings/{docId}",
            "--timeout", "540s",
            "--memory", "512MB",
            "--region", "us-central1"
        ]
        
        print("Updating function timeout...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Function timeout updated successfully!")
            print(result.stdout)
        else:
            print("❌ Error updating function timeout:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    update_function_timeout()


