import json
import re
from openai import OpenAI


_FENCE_OPEN = re.compile(r"^```[a-zA-Z]*\n?")
_FENCE_CLOSE = re.compile(r"\n?```$")
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def _parse_items(content: str | None) -> list[dict]:
    """Parse the LLM response into a list of items, tolerating the common
    ways models wrap JSON: markdown code fences and leading/trailing prose."""
    if not content:
        return []
    text = content.strip()
    if text.startswith("```"):
        text = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", text)).strip()
    try:
        return json.loads(text).get("items", [])
    except json.JSONDecodeError:
        pass
    match = _JSON_OBJECT.search(text)
    if match:
        try:
            return json.loads(match.group(0)).get("items", [])
        except json.JSONDecodeError:
            return []
    return []


SYSTEM_PROMPT_TEMPLATE = """Eres un asistente que extrae información relevante de transcripciones de vídeos (TikTok, YouTube, Instagram Reels, etc.).

Extrae los datos concretos mencionados (productos, obras, lugares, recetas, libros, etc.) y clasifícalos usando una de las categorías permitidas. Si un elemento no encaja claramente, usa la categoría más genérica disponible.

Categorías permitidas: {categories}

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{{
  "items": [
    {{"category": "<una de las categorías permitidas>", "name": "<nombre>", "description": "<descripción breve>"}}
  ]
}}

Si no hay datos relevantes, devuelve {{"items": []}}.
No incluyas explicaciones fuera del JSON."""


def build_system_prompt(category_names: list[str]) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(categories=", ".join(category_names))


def _get_client(llm_config: dict) -> OpenAI:
    return OpenAI(
        base_url=llm_config["base_url"],
        api_key=llm_config.get("api_key") or "not-needed",
    )


def extract_data(
    transcription: str,
    llm_config: dict,
    category_names: list[str],
) -> list[dict]:
    client = _get_client(llm_config)
    response = client.chat.completions.create(
        model=llm_config["model"],
        messages=[
            {"role": "system", "content": build_system_prompt(category_names)},
            {"role": "user", "content": transcription},
        ],
        temperature=0.1,
    )
    return _parse_items(response.choices[0].message.content)
