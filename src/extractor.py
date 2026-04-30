import json
from openai import OpenAI

SYSTEM_PROMPT = """Eres un asistente que extrae información relevante de transcripciones de videos de TikTok.

Extrae los datos concretos mencionados: nombres de software/productos y su utilidad, series/películas y breve sinopsis, música y artista, o cualquier otro elemento relevante.

Responde ÚNICAMENTE con un JSON válido con esta estructura:
{
  "items": [
    {"category": "Software|Serie|Película|Música|Otro", "name": "nombre", "description": "descripción breve"}
  ]
}

Si no hay datos relevantes, devuelve {"items": []}.
No incluyas explicaciones fuera del JSON."""


def _get_client(llm_config: dict) -> OpenAI:
    return OpenAI(
        base_url=llm_config["base_url"],
        api_key=llm_config.get("api_key") or "not-needed",
    )


def extract_data(transcription: str, llm_config: dict) -> list[dict]:
    client = _get_client(llm_config)
    response = client.chat.completions.create(
        model=llm_config["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
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
