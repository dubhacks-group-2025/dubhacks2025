# DubHacks 2025 - AI-Powered 3D Model Generation Platform

A full-stack application that transforms 2D images into 3D models using AI-powered image generation and 3D reconstruction services. The platform processes user-uploaded images through a sophisticated pipeline that generates enhanced versions using Google's Gemini AI and converts them into interactive 3D models.

## Architecture Overview

The application follows a microservices architecture with two main backend components:

1. **FastAPI Backend** - RESTful API service for image generation and processing
2. **Firebase Functions** - Serverless functions for 3D model generation and file processing

## Tech Stack

### Backend Framework
- **FastAPI** - Modern, high-performance web framework for building APIs
- **Uvicorn** - ASGI server for running FastAPI applications
- **Pydantic** - Data validation and serialization using Python type annotations

### Cloud Infrastructure
- **Firebase** - Google's comprehensive development platform
  - **Firestore** - NoSQL document database for storing application data
  - **Firebase Storage** - Cloud storage for images and 3D model files
  - **Firebase Functions** - Serverless compute platform for backend processing
  - **Firebase Admin SDK** - Server-side Firebase integration and authentication

### AI/ML Services
- **Google GenAI (Gemini)** - Generative AI service for image enhancement and generation
- **Tripo3D** - 3D model generation service for converting 2D images to 3D models
- **PIL (Pillow)** - Python Imaging Library for image processing and manipulation

### Data Processing
- **Background Workers** - Custom asynchronous processing system:
  - Image conversion and optimization
  - 3D mesh processing and refinement
  - File format conversion (GLB to USDZ)

### Key Dependencies
- **HTTP Client**: `httpx` for asynchronous HTTP requests
- **Authentication**: `PyJWT` for JWT token handling
- **Environment Management**: `python-dotenv` for configuration
- **Image Processing**: `Pillow` for image manipulation
- **Cloud Storage**: `google-cloud-storage` for file management
- **Database**: `google-cloud-firestore` for data persistence

## Core Functionality

### Image Processing Pipeline
1. **Image Upload** - Users upload 2D images through the web interface
2. **AI Enhancement** - Google Gemini processes the image with custom prompts to generate enhanced versions
3. **3D Generation** - Tripo3D converts the enhanced 2D image into a 3D model
4. **File Conversion** - GLB models are converted to USDZ format for AR/VR compatibility
5. **Storage & Delivery** - Processed files are stored in Firebase Storage and served via CDN

### API Endpoints
- `POST /tasks/generate_image` - Generate enhanced images from text prompts
- `GET /health` - Health check endpoint
- `GET /` - API status and information

### Firebase Functions
- **Image Processing Trigger** - Automatically processes uploaded images
- **3D Model Generation** - Converts enhanced images to 3D models
- **File Conversion** - Handles GLB to USDZ conversion

## Project Structure

```
dubhacks-2025/
├── backend/
│   └── fastapi_app/
│       ├── main.py                 # FastAPI application entry point
│       ├── routes/                 # API route definitions
│       ├── services/               # Core business logic
│       │   ├── nanobanana.py      # Image generation service
│       │   ├── tripo.py           # 3D model generation service
│       │   └── converter.py       # File format conversion
│       └── workers/               # Background processing workers
├── firebase/
│   └── functions/
│       └── main.py                # Firebase Cloud Functions
├── infra/
│   ├── Dockerfile                 # Container configuration
│   └── scripts/                   # Deployment scripts
└── output/                        # Generated 3D model files
```

## Setup and Installation

### Prerequisites
- Python 3.9+
- Node.js 18+
- Firebase CLI
- Google Cloud SDK

### Environment Variables
Create a `.env` file with the following variables:
```
GEMINI_API_KEY=your_gemini_api_key
TRIPO_API_KEY=your_tripo_api_key
FIREBASE_PROJECT_ID=your_firebase_project_id
```

### Backend Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the FastAPI server:
   ```bash
   cd backend/fastapi_app
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Firebase Functions Setup
1. Install Firebase Functions dependencies:
   ```bash
   cd firebase/functions
   pip install -r requirements.txt
   ```

2. Deploy Firebase Functions:
   ```bash
   firebase deploy --only functions
   ```

### Docker Deployment
1. Build the Docker image:
   ```bash
   docker build -f infra/Dockerfile -t dubhacks-backend .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 dubhacks-backend
   ```

## API Usage

### Generate Enhanced Image
```bash
curl -X POST "http://localhost:8000/tasks/generate_image" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A photorealistic close-up of a banana with natural lighting",
    "reference_url": "https://example.com/image.jpg"
  }'
```

### Health Check
```bash
curl http://localhost:8000/health
```

## Development

### Code Organization
- **Services** - Core business logic and external API integrations
- **Routes** - API endpoint definitions and request/response handling
- **Workers** - Background processing and file conversion tasks
- **Utils** - Shared utilities and helper functions

### Key Features
- Asynchronous processing for improved performance
- Comprehensive error handling and logging
- File format conversion pipeline (PNG → GLB → USDZ)
- Firebase integration for scalable cloud storage
- CORS-enabled API for cross-origin requests

## Deployment

The application is designed for cloud deployment with:
- **Firebase Functions** for serverless backend processing
- **Firebase Storage** for file management and CDN delivery
- **Firestore** for real-time data synchronization
- **Docker** support for containerized deployment

## License

This project was developed for DubHacks 2025.
