import os
import warnings
from groq import Groq
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "mixtral-8x7b-32768")

_client_instance = None


def _get_client(api_key: Optional[str] = None) -> Optional[Groq]:
    global _client_instance
    key = api_key or GROQ_API_KEY
    if _client_instance is None and key:
        _client_instance = Groq(api_key=key)
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
            f"[NOTE] Groq API key is missing or invalid. Set GROQ_API_KEY in .env to use the actual LLM."
        )
    return (
        f"Regarding \"{prompt[:100]}...\":\n\n"
        f"This is a fallback response because the Groq API key is not configured. "
        f"Set GROQ_API_KEY in .env to restore full LLM functionality.\n\n"
        f"All other features (vector store, retrieval, agent planning, SSE streaming, PDF upload) work normally."
    )


def generate(prompt: str, api_key: Optional[str] = None, model: Optional[str] = None) -> str:
    model = model or GROQ_MODEL
    if not (api_key or GROQ_API_KEY):
        return _fallback_generate(prompt)

    try:
        client = _get_client(api_key)
        if client is None:
            return _fallback_generate(prompt)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an assistant that answers user queries using provided context. Answer concisely, citing sources by index when appropriate."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        err = str(e)
        if "401" in err or "unauthorized" in err.lower() or "invalid" in err.lower():
            warnings.warn("Groq API key invalid, using fallback generation")
            return _fallback_generate(prompt)
        if "429" in err or "rate" in err.lower():
            warnings.warn("Groq API rate limited, using fallback generation")
            return _fallback_generate(prompt)
        return f"[ERROR_CALLING_GROQ] {err}"
