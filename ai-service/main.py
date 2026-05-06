from flask import Flask, request, jsonify
from ai_model import AIModel
from utils import format_code, validate_prompt
from config import Config

app = Flask(__name__)
ai_model = AIModel()

@app.route('/generate', methods=['POST'])
def generate_code():
    data = request.get_json()
    prompt = data.get('prompt', '')
    
    if not validate_prompt(prompt):
        return jsonify({'error': 'Invalid prompt'}), 400
    
    raw_code = ai_model.generate_code(prompt)
    formatted_code = format_code(raw_code)
    
    return jsonify({'code': formatted_code})

@app.route('/')
def home():
    return "AI Developer 2 API"

if __name__ == '__main__':
    app.run(debug=True)