import os
import warnings
from google import genai
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_client_instance = None


def _get_client(api_key: Optional[str] = None) -> genai.Client:
    global _client_instance
    key = api_key or GEMINI_API_KEY
    if _client_instance is None and key:
        _client_instance = genai.Client(api_key=key)
    return _client_instance


def _fallback_generate(prompt: str) -> str:
    lines = prompt.split("\n")
    context_lines = [l for l in lines if l.startswith("[Source")]
    question_lines = [l for l in lines if l.startswith("User question:")]
    question = question_lines[0].replace("User question:", "").strip() if question_lines else prompt[:200]
    if context_lines:
        return (
            f"Based on retrieved documents, here's what I found about \"{question}\":\n\n"
            f"The knowledge base contains {len(context_lines)} relevant documents. "
            f"They cover topics including: {context_lines[0][:100]}.\n\n"
            f"[NOTE] Gemini API quota is exhausted. Enable billing at https://console.cloud.google.com/apis to use the actual LLM."
        )
    return (
        f"Regarding \"{prompt[:100]}...\":\n\n"
        f"This is a fallback response because the Gemini API quota is currently exhausted. "
        f"Enable billing at https://console.cloud.google.com/apis to restore full LLM functionality.\n\n"
        f"All other features (vector store, retrieval, agent planning, SSE streaming, PDF upload) work normally."
    )


def generate(prompt: str, api_key: Optional[str] = None, model: Optional[str] = None) -> str:
    model = model or GEMINI_MODEL
    if not (api_key or GEMINI_API_KEY):
        return _fallback_generate(prompt)

    try:
        client = _get_client(api_key)
        if client is None:
            return _fallback_generate(prompt)
        response = client.models.generate_content(model=model, contents=prompt)
        return response.text if hasattr(response, 'text') else str(response)
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
            warnings.warn("Gemini API quota exhausted, using fallback generation")
            return _fallback_generate(prompt)
        return f"[ERROR_CALLING_GEMINI] {err}"
