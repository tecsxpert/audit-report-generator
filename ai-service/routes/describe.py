from flask import Blueprint, request, jsonify
from services.groq_client import generate_description

describe_bp = Blueprint("describe", __name__)

@describe_bp.route("/describe", methods=["POST"])
def describe():

    data = request.json
    text = data.get("text")

    if not text:
        return jsonify({"error": "Input required"}), 400

    response = generate_description(text)

    return jsonify({
        "description": response
    })
