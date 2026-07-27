import json
import logging
import re
from functools import lru_cache
from typing import Protocol

from google import genai
from google.genai import types
from openai import OpenAI

from app.core.config import get_settings
from app.rag.prompts import STRICT_SYSTEM_INSTRUCTION


logger = logging.getLogger("pdf_rag.llm")


def parse_groundedness_json(raw: str) -> bool:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            logger.warning("Could not parse groundedness response: %s", raw)
            return False
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            logger.warning("Could not parse groundedness response: %s", raw)
            return False
    return bool(parsed.get("grounded"))


class LLMProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...

    def generate_answer(self, prompt: str) -> str:
        ...

    def check_groundedness(self, answer: str, chunks: list[dict]) -> bool:
        ...


class OpenAIProvider:
    def __init__(self, api_key: str, chat_model: str, embedding_model: str):
        self.client = OpenAI(api_key=api_key)
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def generate_answer(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": STRICT_SYSTEM_INSTRUCTION,
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        if response.usage:
            logger.info(
                "openai_chat_usage prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
                response.usage.total_tokens,
            )
        return response.choices[0].message.content or ""

    def check_groundedness(self, answer: str, chunks: list[dict]) -> bool:
        context = "\n\n".join(
            f"[Page {chunk['page']}]\n{chunk['text']}" for chunk in chunks
        )
        prompt = f"""
Decide whether the answer is fully supported by the context.
Return only JSON with this shape: {{"grounded": true}} or {{"grounded": false}}.

Context:
{context}

Answer:
{answer}
""".strip()
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": "You are a strict groundedness checker."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        return parse_groundedness_json(raw)


class GeminiProvider:
    def __init__(
        self,
        api_key: str,
        chat_model: str,
        embedding_model: str,
        embedding_dimensions: int,
    ):
        self.client = genai.Client(api_key=api_key)
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions

    def _embed_contents(self, contents: list[str]) -> list[list[float]]:
        response = self.client.models.embed_content(
            model=self.embedding_model,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)],
                )
                for content in contents
            ],
            config=types.EmbedContentConfig(
                output_dimensionality=self.embedding_dimensions,
            ),
        )
        return [list(embedding.values) for embedding in response.embeddings]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        documents = [f"title: none | text: {text}" for text in texts]
        return self._embed_contents(documents)

    def embed_query(self, text: str) -> list[float]:
        return self._embed_contents([f"task: search result | query: {text}"])[0]

    def generate_answer(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.chat_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=STRICT_SYSTEM_INSTRUCTION,
            ),
        )
        return response.text or ""

    def check_groundedness(self, answer: str, chunks: list[dict]) -> bool:
        context = "\n\n".join(
            f"[Page {chunk['page']}]\n{chunk['text']}" for chunk in chunks
        )
        prompt = f"""
Decide whether the answer is fully supported by the context.
Return only JSON with this shape: {{"grounded": true}} or {{"grounded": false}}.

Context:
{context}

Answer:
{answer}
""".strip()
        response = self.client.models.generate_content(
            model=self.chat_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="You are a strict groundedness checker.",
                response_mime_type="application/json",
            ),
        )
        raw = response.text or "{}"
        return parse_groundedness_json(raw)


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "gemini":
        settings.require_gemini()
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            chat_model=settings.gemini_chat_model,
            embedding_model=settings.gemini_embedding_model,
            embedding_dimensions=settings.gemini_embedding_dimensions,
        )

    settings.require_openai()
    return OpenAIProvider(
        api_key=settings.openai_api_key,
        chat_model=settings.openai_chat_model,
        embedding_model=settings.openai_embedding_model,
    )
