"""
Flask application main entry point
"""
from flask import Flask, request, jsonify
from app.config import Config
from app.openai_service import OpenAIService
from app.linkedin_service import LinkedInService

app = Flask(__name__)

# Initialize services
openai_service = OpenAIService()
linkedin_service = LinkedInService()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "LinkedIn Job Assistant"
    }), 200


@app.route('/api/classify', methods=['POST'])
def classify_intent():
    """
    Classify user message intent
    
    Request body:
    {
        "message": "user message text"
    }
    
    Response:
    {
        "intent": "PROFILE|JOBS|UNKNOWN",
        "confidence": 0.95,
        "job_params": {...}  # if intent is JOBS
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({"error": "Missing 'message' field"}), 400
        
        message = data['message']
        result = openai_service.classify_intent(message)
        
        return jsonify({
            "intent": result.intent,
            "confidence": result.confidence,
            "job_params": result.job_params.dict() if result.job_params else None
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """
    Get LinkedIn profile
    
    Response:
    {
        "headline": "...",
        "summary": "...",
        "experience": [...],
        "education": [...]
    }
    """
    try:
        profile = linkedin_service.get_my_profile()
        return jsonify(profile), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/jobs/search', methods=['POST'])
def search_jobs():
    """
    Search for jobs
    
    Request body:
    {
        "query": "Python Developer",
        "location": "Berlin",  # optional
        "keywords": ["Django", "Flask"]  # optional
    }
    
    Response:
    {
        "jobs": [
            {
                "title": "...",
                "company": "...",
                "location": "...",
                "type": "...",
                "description": "...",
                "url": "..."
            }
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' field"}), 400
        
        query = data['query']
        location = data.get('location')
        keywords = data.get('keywords')
        
        jobs = linkedin_service.search_jobs(
            query=query,
            location=location,
            keywords=keywords
        )
        
        return jsonify({"jobs": jobs}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """
    Webhook endpoint for Telegram bot
    (Alternative to long polling)
    """
    # This can be implemented for webhook mode
    # For now, we use long polling in telegram_bot.py
    return jsonify({"status": "webhook received"}), 200


def create_app():
    """Application factory"""
    # Validate configuration
    Config.validate()
    
    return app


if __name__ == '__main__':
    # Validate config
    Config.validate()
    
    # Run Flask app
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )

