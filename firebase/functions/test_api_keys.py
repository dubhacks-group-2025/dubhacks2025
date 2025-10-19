from firebase_functions import https_fn
from firebase_admin import initialize_app
import os

# Initialize Firebase Admin SDK
initialize_app()

@https_fn.on_request()
def test_api_keys(req: https_fn.Request) -> https_fn.Response:
    """Test function to check if API keys are accessible."""
    try:
        # Test environment variables
        gemini_env = os.getenv("GEMINI_API_KEY")
        tripo_env = os.getenv("TRIPO_API_KEY")
        
        # Test Firebase config
        try:
            from firebase_functions import config
            gemini_config = config.gemini.api_key
            tripo_config = config.tripo.api_key
        except Exception as e:
            gemini_config = f"Error: {e}"
            tripo_config = f"Error: {e}"
        
        result = {
            "environment_variables": {
                "GEMINI_API_KEY": gemini_env[:10] + "..." if gemini_env else "None",
                "TRIPO_API_KEY": tripo_env[:10] + "..." if tripo_env else "None"
            },
            "firebase_config": {
                "gemini.api_key": gemini_config[:10] + "..." if isinstance(gemini_config, str) and len(gemini_config) > 10 else str(gemini_config),
                "tripo.api_key": tripo_config[:10] + "..." if isinstance(tripo_config, str) and len(tripo_config) > 10 else str(tripo_config)
            }
        }
        
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
        }
        
        import json
        return https_fn.Response(json.dumps(result, indent=2), 200, headers)
        
    except Exception as e:
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json',
        }
        return https_fn.Response(f'{{"error": "{str(e)}"}}', 500, headers)


