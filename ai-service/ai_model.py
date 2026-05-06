import openai
from config import Config

class AIModel:
    def __init__(self):
        openai.api_key = Config.OPENAI_API_KEY
        self.model = Config.MODEL

    def generate_code(self, prompt: str) -> str:
        """Generate code based on the prompt."""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert Python developer. Generate clean, efficient code."},
                    {"role": "user", "content": f"Generate Python code for: {prompt}"}
                ],
                max_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating code: {str(e)}"