# Exam Preparation Application

## Recent Updates

### Gemini API Integration
The application now uses Google's Gemini API for AI text processing and summarization, replacing the previous Hugging Face transformers implementation.

## Setup Instructions

### API Key Configuration
1. Obtain a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Replace the placeholder in `app.py` with your actual API key:
   ```python
   genai.configure(api_key="YOUR_GEMINI_API_KEY")  # Replace with your actual API key
   ```
   
   For production environments, it's recommended to use environment variables:
   ```python
   import os
   genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
   ```

### Dependencies
Ensure you have the required dependencies installed:
```
pip install flask flask-sqlalchemy flask-login werkzeug PyPDF2 google-generativeai
```

## Features
- User authentication and progress tracking
- Study plan generation for 3-month and 6-month tracks
- PDF material processing and summarization using Google's Gemini AI
- Quiz generation and assessment
- Daily task management and streak tracking

## Usage
Run the application with:
```
python app.py
```

Access the web interface at http://localhost:5000