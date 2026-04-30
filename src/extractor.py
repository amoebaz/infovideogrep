import json
from openai import OpenAI


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
    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        return data.get("items", [])
    except json.JSONDecodeError:
        return []
