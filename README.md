# InfoVideoGrep

Bot que captura vídeos reenviados a Telegram (TikTok, YouTube, Instagram Reels y vídeos largos de YouTube), los transcribe con [faster-whisper](https://github.com/SYSTRAN/faster-whisper), extrae información estructurada con un LLM y la añade como entradas en los ficheros markdown de tu vault de Obsidian, agrupadas por tema.

Pensado para no perder nunca más una recomendación que ves de pasada en un Reel o un Short: software, series, películas, libros, lugares, recetas… cada cosa va a su categoría y queda anotada con la fecha y el enlace al vídeo original.

## Cómo funciona

```
Telegram bot ──► parser ──► descarga (yt-dlp / Telegram API) ──► Whisper
                                                                     │
                                                                     ▼
                                              Pendientes/<fecha> - <slug>.md
                                              (transcripción + frontmatter,
                                               estado: pendiente)
                                                                     │
                                                                     ▼
                            LLM (OpenRouter)  ◄── transcripción
                                    │
                                    ▼ (fallback: Ollama local)
                              JSON estructurado
                                    │
                    ┌───────────────┴────────────────┐
                    ▼ éxito                           ▼ fallo
       ficheros de resumen por tema            se queda en Pendientes/
       + Procesadas/ (estado: procesada)       con estado: error_llm
                                                (la tarea de Claude cada
                                                 6 h la reprocesa)
```

1. **Captura**: el bot polea `getUpdates` de Telegram. Se queda con mensajes que contienen un vídeo reenviado o un enlace soportado.
2. **Descarga**:
   - Reenvíos directos → API de Telegram.
   - Enlaces → `yt-dlp`.
   - Antes de descargar URLs comprueba la duración con `yt-dlp --skip-download` y descarta lo que excede `processing.max_duration_seconds`.
3. **Transcripción**: faster-whisper con el modelo configurado (por defecto `medium` en GPU CUDA). El resultado se guarda SIEMPRE como fichero markdown con frontmatter (`fecha`, `url`, `estado`, `intentos`) en `Pendientes/` dentro del vault, antes de llamar al LLM — así nunca se pierde una transcripción aunque falle la extracción.
4. **Extracción**: prompt al LLM con la lista de categorías permitidas. Se prueban en orden los modelos de `llm.models` (los `:free` de OpenRouter rotan entre 429/503/ok), con un reintento por modelo. Si todos fallan, cae a Ollama local (que se autoarranca y descarga el modelo si hace falta). La respuesta se parsea tolerando JSON envuelto en bloques markdown.
5. **Volcado**:
   - Si la extracción tiene éxito, cada item se añade bajo la cabecera `## YYYY-MM-DD` del fichero de resumen que le corresponda según `markdown.summary_files`, y la transcripción se mueve a `Procesadas/` con `estado: procesada`.
   - Si el LLM falla en todos los intentos, la transcripción se queda en `Pendientes/` con `estado: error_llm`. Una tarea programada de Claude (cada 6 h, ver [`docs/cowork-task.md`](docs/cowork-task.md)) la reprocesa más tarde.

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
VIDEOINBOX_DIR=/ruta/absoluta/a/tu/vault/VideoInbox
```

- **`TELEGRAM_BOT_TOKEN`**: créalo con `@BotFather` en Telegram (`/newbot`).
- **`OPENROUTER_API_KEY`**: gratis en [openrouter.ai](https://openrouter.ai) (los modelos `:free` no consumen crédito).
- **`VIDEOINBOX_DIR`**: ruta a la carpeta donde el bot creará `Pendientes/`, `Procesadas/` y los ficheros de resumen por tema. Si la apuntas dentro de tu vault de Obsidian, lo verás directamente desde ahí.

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
  - {name: "IA",        icon: "🤖"}
  - {name: "Serie",     icon: "📺"}
  - {name: "Película",  icon: "🎬"}
  - {name: "Música",    icon: "🎵"}
  - {name: "Libro",     icon: "📚"}
  - {name: "Lugar",     icon: "📍"}
  - {name: "Receta",    icon: "🍳"}
  - {name: "Otro",      icon: "📌"}

markdown:
  # Carpeta del vault de Obsidian donde viven Pendientes/, Procesadas/
  # y los ficheros de resumen por tema.
  vault_inbox_dir: "${VIDEOINBOX_DIR}"
  # Mapeo categoría → fichero de resumen. Categorías sin mapeo caen en
  # default_summary_file.
  summary_files:
    - {file: "Series y Películas.md", categories: ["Serie", "Película"]}
    - {file: "Software.md",           categories: ["Software"]}
    - {file: "IA.md",                 categories: ["IA"]}
    - {file: "Otros.md",              categories: ["Música", "Libro", "Lugar", "Receta", "Otro"]}
  default_summary_file: "Otros.md"
```

Las cadenas con `${VAR}` se sustituyen al cargar la config con valores del `.env`.

#### Categorías

Edita la lista a tu gusto. Lo que escribas en `name` se inyecta literalmente en el prompt del LLM como conjunto de categorías permitidas — añade, quita o renombra para adaptarlo a lo que tú consumes. El `icon` se usa al formatear las entradas en el markdown. Si añades una categoría nueva, recuerda incluirla en `markdown.summary_files` (o dejarla caer en `default_summary_file`) para que sepas en qué fichero buscarla.

#### Duración máxima

`processing.max_duration_seconds` evita que un podcast de 2 h en YouTube te bloquee Whisper durante 30 min. Si excede el límite, el vídeo se descarta sin transcribir y se archiva directamente en `Procesadas/` con `estado: duracion_excedida` — no hay nada que reprocesar.

### Estructura del vault

Dentro de `VIDEOINBOX_DIR` el bot mantiene:

```
VideoInbox/
├── Pendientes/              transcripciones sin resumir (estado: pendiente | error_llm)
├── Procesadas/              transcripciones ya resumidas o descartadas
├── Series y Películas.md    resúmenes de Serie / Película
├── Software.md              resúmenes de Software
├── IA.md                    resúmenes de IA
└── Otros.md                 resto de categorías (default_summary_file)
```

Cada transcripción se guarda como un fichero markdown con frontmatter:

```yaml
---
fecha: 2026-07-13T10:32:00
url: https://...
estado: pendiente
intentos: 0
---
```

Estados posibles:

| Estado                | Significado                                                             | Carpeta       |
|------------------------|-------------------------------------------------------------------------|---------------|
| `pendiente`            | transcrita, esperando a que el LLM la procese                           | `Pendientes/` |
| `error_llm`            | el LLM falló en todos los intentos; queda para reprocesar               | `Pendientes/` |
| `procesada`            | items ya extraídos y volcados en su fichero de resumen                  | `Procesadas/` |
| `duracion_excedida`    | vídeo descartado por exceder `processing.max_duration_seconds`          | `Procesadas/` |
| `transcripcion_vacia`  | Whisper no produjo texto                                                 | `Procesadas/` |

Las transcripciones que quedan en `Pendientes/` con `estado: error_llm` las recoge la tarea programada de Claude (cada 6 h) descrita en [`docs/cowork-task.md`](docs/cowork-task.md), que las clasifica, reparte los items en los ficheros de resumen y las mueve a `Procesadas/`.

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
3. En el siguiente poll del bot, la transcripción aparece en `Pendientes/` y, si el LLM la clasifica sin problemas, el resumen aparece también en el fichero de tema correspondiente.

## Estructura del proyecto

```
src/
├── config.py        Carga config.yaml y expande ${VAR} desde .env
├── telegram.py      Polling, parser de mensajes, descarga de adjuntos
├── downloader.py    yt-dlp para URLs, guard de duración
├── transcriber.py   faster-whisper (caché de modelo)
├── extractor.py     Prompt + llamada al LLM (OpenAI-compatible)
├── obsidian.py      Guarda transcripciones en Pendientes/Procesadas, enruta items a sus ficheros de resumen y formatea entradas
└── main.py          Orquestación, modo watch, fallback LLM

tests/               Tests unitarios (pytest)
docs/cowork-task.md  Prompt de la tarea periódica que reprocesa Pendientes/
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

[MIT](LICENSE) © Lolo
