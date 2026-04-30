# InfoVideoGrep

Bot que captura vídeos reenviados a Telegram (TikTok, YouTube, Instagram Reels y vídeos largos de YouTube), los transcribe con [faster-whisper](https://github.com/SYSTRAN/faster-whisper), extrae información estructurada con un LLM y la añade como entradas en un fichero markdown que puedes leer desde Obsidian o cualquier otro editor.

Pensado para no perder nunca más una recomendación que ves de pasada en un Reel o un Short: software, series, películas, libros, lugares, recetas… cada cosa va a su categoría y queda anotada con la fecha y el enlace al vídeo original.

## Cómo funciona

```
Telegram bot ──► parser ──► descarga (yt-dlp / Telegram API) ──► Whisper
                                                                     │
                                                                     ▼
                            LLM (OpenRouter)  ◄── transcripción
                                    │
                                    ▼ (fallback: Ollama local)
                              JSON estructurado
                                    │
                                    ▼
                           inbox.md (agrupado por fecha)
```

1. **Captura**: el bot polea `getUpdates` de Telegram. Se queda con mensajes que contienen un vídeo reenviado o un enlace soportado.
2. **Descarga**:
   - Reenvíos directos → API de Telegram.
   - Enlaces → `yt-dlp`.
   - Antes de descargar URLs comprueba la duración con `yt-dlp --skip-download` y descarta lo que excede `processing.max_duration_seconds`.
3. **Transcripción**: faster-whisper con el modelo configurado (por defecto `medium` en GPU CUDA).
4. **Extracción**: prompt al LLM principal con la lista de categorías permitidas. Si falla dos veces, cae a Ollama local (que se autoarranca y descarga el modelo si hace falta).
5. **Volcado**: añade la entrada bajo la cabecera `## YYYY-MM-DD` del markdown configurado.

## Plataformas soportadas

| Plataforma           | Formato del enlace                        |
|----------------------|-------------------------------------------|
| TikTok               | `tiktok.com/...`, `vm.tiktok.com/...`     |
| YouTube              | `youtube.com/watch?v=...`, `youtu.be/...` |
| YouTube Shorts       | `youtube.com/shorts/...`                  |
| Instagram Reels      | `instagram.com/reel/...`, `/reels/...`    |
| Vídeo reenviado      | adjunto directo en el chat de Telegram    |

## Instalación

Requisitos previos:
- Python 3.10+
- `ffmpeg` (lo necesita yt-dlp para algunos formatos).
- GPU NVIDIA con CUDA si quieres usar el modelo `medium` o superior de Whisper. En CPU también funciona con modelos pequeños (`tiny`, `base`).
- (Opcional) [Ollama](https://ollama.com) si quieres fallback LLM local.

```bash
git clone https://github.com/amoebaz/infovideogrep.git
cd infovideogrep
./install.sh
```

`install.sh` crea un `venv/`, instala las dependencias Python, las librerías CUDA si aplica y comprueba que tengas yt-dlp y Ollama disponibles.

## Configuración

### Variables sensibles: `.env`

Crea un `.env` (no se sube a git) copiando la plantilla:

```bash
cp .env.example .env
```

Y rellena:

```env
TELEGRAM_BOT_TOKEN=tu-token-de-botfather
OPENROUTER_API_KEY=tu-api-key-de-openrouter
MARKDOWN_INBOX_PATH=/ruta/absoluta/a/tu/VideoInbox.md
```

- **`TELEGRAM_BOT_TOKEN`**: créalo con `@BotFather` en Telegram (`/newbot`).
- **`OPENROUTER_API_KEY`**: gratis en [openrouter.ai](https://openrouter.ai) (los modelos `:free` no consumen crédito).
- **`MARKDOWN_INBOX_PATH`**: ruta al fichero markdown donde se añadirán las entradas. Si lo apuntas dentro de tu vault de Obsidian, lo verás directamente desde ahí.

### Opciones del proyecto: `config.yaml`

```yaml
telegram:
  bot_token: "${TELEGRAM_BOT_TOKEN}"
  offset_file: "./data/telegram_offset.txt"

whisper:
  model: "medium"             # tiny | base | small | medium | large-v3

processing:
  max_duration_seconds: 3600  # null para deshabilitar el guard

llm:
  base_url: "https://openrouter.ai/api/v1"
  api_key: "${OPENROUTER_API_KEY}"
  model: "minimax/minimax-m2.5:free"

llm_fallback:                 # opcional
  base_url: "http://localhost:11434/v1"
  api_key: ""
  model: "qwen2.5:3b"

categories:
  - {name: "Software",  icon: "🖥️"}
  - {name: "Serie",     icon: "📺"}
  - {name: "Película",  icon: "🎬"}
  - {name: "Música",    icon: "🎵"}
  - {name: "Libro",     icon: "📚"}
  - {name: "Lugar",     icon: "📍"}
  - {name: "Receta",    icon: "🍳"}
  - {name: "Otro",      icon: "📌"}

markdown:
  inbox_path: "${MARKDOWN_INBOX_PATH}"
```

Las cadenas con `${VAR}` se sustituyen al cargar la config con valores del `.env`.

#### Categorías

Edita la lista a tu gusto. Lo que escribas en `name` se inyecta literalmente en el prompt del LLM como conjunto de categorías permitidas — añade, quita o renombra para adaptarlo a lo que tú consumes. El `icon` se usa al formatear las entradas en el markdown.

#### Duración máxima

`processing.max_duration_seconds` evita que un podcast de 2 h en YouTube te bloquee Whisper durante 30 min. Si excede el límite, se anota una entrada `⏱️ Duración excedida` en el inbox y se ignora el vídeo.

## Uso

```bash
./run.sh                # un único poll y termina
./run.sh --watch        # bucle continuo, polea cada 60 s
./run.sh --watch 30     # bucle continuo, polea cada 30 s
```

`--watch` es Ctrl+C para detener.

Para usarlo en producción, lo más cómodo es un servicio systemd o un `tmux` con `./run.sh --watch 60`.

### Cómo enviar vídeos al bot

1. Inicia conversación con tu bot en Telegram.
2. Reenvíale un vídeo (TikTok, Reel, Short, vídeo de YouTube...) o pégale un enlace soportado.
3. En el siguiente poll del bot, la entrada aparece en tu markdown.

## Estructura del proyecto

```
src/
├── config.py        Carga config.yaml y expande ${VAR} desde .env
├── telegram.py      Polling, parser de mensajes, descarga de adjuntos
├── downloader.py    yt-dlp para URLs, guard de duración
├── transcriber.py   faster-whisper (caché de modelo)
├── extractor.py     Prompt + llamada al LLM (OpenAI-compatible)
├── obsidian.py      Formato de entradas y append agrupado por fecha
└── main.py          Orquestación, modo watch, fallback LLM

tests/               Tests unitarios (pytest)
config.yaml          Esquema (con placeholders ${VAR})
.env.example         Plantilla de variables sensibles
install.sh / run.sh  Helpers
```

## Tests

```bash
source venv/bin/activate
python -m pytest tests/ -q
```

## Roadmap

- [ ] Podcasts vía RSS / URL directa al MP3.
- [ ] Modo audio-only en yt-dlp para acelerar Whisper en vídeos largos.
- [ ] Deduplicación: detectar vídeo ya procesado por URL/file_id.

## Licencia

Sin licencia explícita por ahora — código personal. Avisa si quieres reutilizarlo y abrimos una.
