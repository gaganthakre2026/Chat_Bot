NOT_FOUND_ANSWER = "I don't have information about that."

STRICT_SYSTEM_INSTRUCTION = (
    "You are a PDF Q&A assistant. You must answer using ONLY the document context "
    "provided in the user message. Never use outside knowledge, assumptions, or general "
    "world facts. If the context does not contain the answer, respond exactly with the "
    f'not-found sentence specified in the user message: "{NOT_FOUND_ANSWER}". '
    "Cite page numbers from the context when answering."
)


def build_grounded_answer_prompt(question: str, chunks: list[dict]) -> str:
    context = "\n\n".join(
        f"[Page {chunk['page']} | Score {chunk['score']:.2f}]\n{chunk['text']}"
        for chunk in chunks
    )
    return f"""
Answer the question using ONLY the document context below.

Strict rules:
- Use only facts explicitly stated in the context chunks.
- Do not guess, infer beyond the text, or add information from outside the document.
- If the answer is not in the context, respond exactly:
  "{NOT_FOUND_ANSWER}"
- Mention the page number(s) used in your answer.

Document context:
{context}

Question: {question}
""".strip()
