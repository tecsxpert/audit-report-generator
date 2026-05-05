"""
Input Sanitization Module for Flask AI Service
AI Developer 3 Responsibility
Sanitizes all user inputs to prevent injection attacks and XSS vulnerabilities
"""

import re
import html
import logging
from typing import Any, Dict, List
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)


class InputSanitizer:
    """Sanitizes and validates user input to prevent security vulnerabilities"""
    
    # Patterns for dangerous content detection
    SQL_INJECTION_PATTERNS = [
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b|\bAND\b)(\s+1\s*=\s*1)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers like onclick, onload, etc.
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+previous\s+instructions?",
        r"disregard.*instructions?",
        r"forget.*instructions?",
        r"system.*prompt",
        r"summarize.*above",
        r"new\s+instructions?:",
        r"begin\s+test",
        r"admin\s+mode",
    ]
    
    @staticmethod
    def strip_html_tags(text: str) -> str:
        """Remove HTML tags from text"""
        if not isinstance(text, str):
            return text
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # HTML decode entities
        text = html.unescape(text)
        return text.strip()
    
    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """Detect potential SQL injection attempts"""
        if not isinstance(text, str):
            return False
        
        # Case-insensitive check
        text_upper = text.upper()
        
        for pattern in InputSanitizer.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                logger.warning(f"SQL Injection attempt detected: {text[:100]}")
                return True
        
        return False
    
    @staticmethod
    def detect_xss_attempt(text: str) -> bool:
        """Detect potential XSS attempts"""
        if not isinstance(text, str):
            return False
        
        for pattern in InputSanitizer.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"XSS attempt detected: {text[:100]}")
                return True
        
        return False
    
    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        """Detect potential prompt injection attacks"""
        if not isinstance(text, str):
            return False
        
        text_lower = text.lower()
        
        for pattern in InputSanitizer.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                logger.warning(f"Prompt injection attempt detected: {text[:100]}")
                return True
        
        return False
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 5000) -> str:
        """
        Sanitize a string input
        
        Args:
            text: Input string to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            ValueError: If injection attempts are detected
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
        
        # Check length
        if len(text) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length}")
        
        # Check for injection attempts
        if InputSanitizer.detect_sql_injection(text):
            raise ValueError("SQL injection attempt detected")
        
        if InputSanitizer.detect_xss_attempt(text):
            raise ValueError("XSS attempt detected")
        
        if InputSanitizer.detect_prompt_injection(text):
            raise ValueError("Prompt injection attempt detected")
        
        # Strip HTML tags
        sanitized = InputSanitizer.strip_html_tags(text)
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], max_length: int = 5000) -> Dict[str, Any]:
        """
        Sanitize all string values in a dictionary
        
        Args:
            data: Dictionary to sanitize
            max_length: Maximum allowed string length
            
        Returns:
            Sanitized dictionary
            
        Raises:
            ValueError: If dangerous content is detected
        """
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputSanitizer.sanitize_string(value, max_length)
            elif isinstance(value, dict):
                sanitized[key] = InputSanitizer.sanitize_dict(value, max_length)
            elif isinstance(value, list):
                sanitized[key] = InputSanitizer.sanitize_list(value, max_length)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def sanitize_list(data: List[Any], max_length: int = 5000) -> List[Any]:
        """
        Sanitize all string values in a list
        
        Args:
            data: List to sanitize
            max_length: Maximum allowed string length
            
        Returns:
            Sanitized list
        """
        sanitized = []
        
        for item in data:
            if isinstance(item, str):
                sanitized.append(InputSanitizer.sanitize_string(item, max_length))
            elif isinstance(item, dict):
                sanitized.append(InputSanitizer.sanitize_dict(item, max_length))
            elif isinstance(item, list):
                sanitized.append(InputSanitizer.sanitize_list(item, max_length))
            else:
                sanitized.append(item)
        
        return sanitized


def sanitize_input(f):
    """
    Decorator to automatically sanitize JSON request body
    
    Usage:
        @app.route('/endpoint', methods=['POST'])
        @sanitize_input
        def my_endpoint():
            data = request.get_json()  # Already sanitized
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get JSON data
            data = request.get_json()
            
            if data:
                # Sanitize the data
                if isinstance(data, dict):
                    sanitized_data = InputSanitizer.sanitize_dict(data)
                elif isinstance(data, list):
                    sanitized_data = InputSanitizer.sanitize_list(data)
                else:
                    sanitized_data = data
                
                # Replace request data with sanitized version
                request._cached_data = sanitized_data
                
                # Override get_json to return sanitized data
                original_get_json = request.get_json
                request.get_json = lambda force=False, silent=False, cache=True: sanitized_data
            
            return f(*args, **kwargs)
        
        except ValueError as e:
            logger.error(f"Input validation error: {str(e)}")
            return jsonify({
                "error": "Invalid input",
                "message": str(e),
                "status": 400
            }), 400
        
        except Exception as e:
            logger.error(f"Unexpected error in sanitization: {str(e)}")
            return jsonify({
                "error": "Server error",
                "status": 500
            }), 500
    
    return decorated_function


def validate_input_length(max_length: int = 5000):
    """
    Decorator to validate input length
    
    Usage:
        @app.route('/endpoint', methods=['POST'])
        @validate_input_length(max_length=10000)
        def my_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json()
                
                if data:
                    # Check total data size
                    import json
                    data_str = json.dumps(data)
                    
                    if len(data_str) > max_length:
                        return jsonify({
                            "error": "Request body too large",
                            "message": f"Request exceeds maximum size of {max_length} bytes",
                            "status": 413
                        }), 413
                
                return f(*args, **kwargs)
            
            except Exception as e:
                logger.error(f"Error validating input length: {str(e)}")
                return jsonify({
                    "error": "Server error",
                    "status": 500
                }), 500
        
        return decorated_function
    
    return decorator
