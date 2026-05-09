from flask import Blueprint

describe_bp = Blueprint('describe', __name__)
from flask import Blueprint, request, jsonify
from services.groq_client import call_groq
from datetime import datetime
import json
import os

describe_bp = Blueprint('describe', __name__)

# Load the prompt template once when app starts
PROMPT_PATH = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'describe_prompt.txt')
with open(PROMPT_PATH, 'r') as f:
    DESCRIBE_PROMPT_TEMPLATE = f.read()


@describe_bp.route('/describe', methods=['POST'])
def describe():
    # Step 1: Get and validate request body
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body is required"}), 400

    audit_input = data.get('audit_input', '').strip()

    if not audit_input:
        return jsonify({"error": "audit_input field is required"}), 400

    if len(audit_input) < 10:
        return jsonify({"error": "audit_input is too short. Please provide more detail."}), 400

    if len(audit_input) > 2000:
        return jsonify({"error": "audit_input is too long. Maximum 2000 characters."}), 400

    # Step 2: Build the prompt
    prompt = DESCRIBE_PROMPT_TEMPLATE.replace("{audit_input}", audit_input)

    # Step 3: Call Groq
    try:
        raw_response = call_groq(prompt, temperature=0.3)
    except Exception as e:
        return jsonify({
            "error": "AI service temporarily unavailable",
            "detail": str(e),
            "is_fallback": True
        }), 503

    # Step 4: Parse the JSON response from Groq
    try:
        ai_result = json.loads(raw_response)
    except json.JSONDecodeError:
        return jsonify({
            "error": "AI returned invalid format",
            "raw_response": raw_response,
            "is_fallback": True
        }), 500

    # Step 5: Return the final structured response
    return jsonify({
        "success": True,
        "data": ai_result,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "meta": {
            "model_used": "llama-3.3-70b-versatile",
            "cached": False
        }
    }), 200
