from app.llm.gemini_client import generate

result = generate('Explain RAG in AI in one sentence')
print('\n[OK] Gemini response received:')
print(result[:250])
