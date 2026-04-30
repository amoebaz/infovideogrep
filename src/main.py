import argparse
import logging
import os
import shutil
import subprocess
import tempfile
import time
from datetime import date

from src.config import load_config
from src.telegram import parse_message, get_updates, read_offset, write_offset
from src.downloader import download_video
from src.transcriber import transcribe
from src.extractor import extract_data
from src.obsidian import format_entry, append_to_inbox

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _ensure_ollama_running(model: str) -> None:
    """Start ollama serve if not already running, then pull the model if needed."""
    try:
        import httpx
        httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        logger.info("Ollama already running")
    except Exception:
        if not shutil.which("ollama"):
            raise RuntimeError("ollama is not installed")
        logger.info("Starting ollama serve...")
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Wait for it to be ready
        for _ in range(15):
            time.sleep(1)
            try:
                import httpx
                httpx.get("http://localhost:11434/api/tags", timeout=2.0)
                break
            except Exception:
                continue
        else:
            raise RuntimeError("ollama failed to start within 15 seconds")
        logger.info("Ollama started")

    # Ensure the model is available (pulls if not present)
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True, text=True, timeout=10,
    )
    model_base = model.split(":")[0] if ":" in model else model
    if model_base not in result.stdout:
        logger.info(f"Pulling ollama model {model}...")
        subprocess.run(
            ["ollama", "pull", model],
            timeout=600,
        )


def _extract_with_fallback(
    text: str,
    llm_config: dict,
    llm_fallback_config: dict | None,
) -> list[dict] | None:
    """Try primary LLM with retry, fall back to secondary if configured."""
    # Try primary LLM (2 attempts)
    for attempt in range(2):
        try:
            return extract_data(text, llm_config)
        except Exception as e:
            logger.warning(f"Primary LLM attempt {attempt + 1} failed: {e}")

    # Try fallback LLM if configured
    if llm_fallback_config:
        logger.info("Switching to fallback LLM (Ollama)...")
        try:
            _ensure_ollama_running(llm_fallback_config["model"])
            return extract_data(text, llm_fallback_config)
        except Exception as e:
            logger.warning(f"Fallback LLM failed: {e}")

    return None


def process_message(
    parsed: dict,
    bot_token: str,
    whisper_model: str,
    llm_config: dict,
    inbox_path: str,
    tmp_dir: str,
    llm_fallback_config: dict | None = None,
) -> None:
    today = date.today().isoformat()
    url = parsed.get("url", "video reenviado sin enlace")

    # Download
    video_path = download_video(parsed, tmp_dir, bot_token)
    logger.info(f"Downloaded: {video_path}")

    # Transcribe
    text = transcribe(video_path, model_size=whisper_model)
    logger.info(f"Transcription ({len(text)} chars): {text[:100]}...")

    # Clean up video file
    if os.path.exists(video_path):
        os.remove(video_path)

    # Handle empty transcription
    if not text.strip():
        entry = format_entry([], url, date_str=today, failed=True)
        append_to_inbox(inbox_path, entry, date_str=today)
        logger.warning("Empty transcription, marked for manual review")
        return

    # Extract data: try primary LLM, then fallback if configured
    items = _extract_with_fallback(text, llm_config, llm_fallback_config)

    if items is None:
        # Save raw transcription as fallback
        entry = f"- 📝 **Transcripción sin procesar**: \"{text[:200]}...\"\n  [enlace al video]({url})\n"
        append_to_inbox(inbox_path, entry, date_str=today)
        logger.error("LLM extraction failed, saved raw transcription")
        return

    entry = format_entry(items, url, date_str=today)
    append_to_inbox(inbox_path, entry, date_str=today)
    logger.info(f"Added {len(items)} items to inbox")


def poll_once(config: dict) -> int:
    """Poll Telegram for pending messages and process them. Returns count of processed messages."""
    bot_token = config["telegram"]["bot_token"]
    offset_file = config["telegram"]["offset_file"]
    whisper_model = config["whisper"]["model"]
    llm_config = config["llm"]
    llm_fallback_config = config.get("llm_fallback")
    inbox_path = config["obsidian"]["inbox_path"]

    offset = read_offset(offset_file)
    updates = get_updates(bot_token, offset)

    if not updates:
        return 0

    logger.info(f"Processing {len(updates)} updates")
    processed = 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        for update in updates:
            message = update.get("message", {})
            parsed = parse_message(message)

            if parsed is None:
                logger.debug(f"Skipping irrelevant message {message.get('message_id')}")
            else:
                try:
                    process_message(
                        parsed=parsed,
                        bot_token=bot_token,
                        whisper_model=whisper_model,
                        llm_config=llm_config,
                        inbox_path=inbox_path,
                        tmp_dir=tmp_dir,
                        llm_fallback_config=llm_fallback_config,
                    )
                    processed += 1
                except Exception as e:
                    logger.error(f"Failed to process message: {e}")

            # Update offset after each message
            new_offset = update["update_id"] + 1
            write_offset(offset_file, new_offset)

    return processed


def main():
    parser = argparse.ArgumentParser(description="InfoVideoGrep — extract info from TikTok videos")
    parser.add_argument(
        "--watch", "-w",
        type=int,
        nargs="?",
        const=60,
        default=None,
        metavar="SECONDS",
        help="Run in loop, polling every N seconds (default: 60)",
    )
    args = parser.parse_args()

    config_path = os.environ.get("INFOVIDEOGREP_CONFIG", "config.yaml")
    config = load_config(config_path)

    if args.watch is not None:
        interval = args.watch
        logger.info(f"Watch mode: polling every {interval}s (Ctrl+C to stop)")
        try:
            while True:
                count = poll_once(config)
                if count == 0:
                    logger.info(f"No new messages, waiting {interval}s...")
                else:
                    logger.info(f"Processed {count} messages, waiting {interval}s...")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Watch mode stopped")
    else:
        count = poll_once(config)
        if count == 0:
            logger.info("No new messages")
        else:
            logger.info(f"Done, processed {count} messages")


if __name__ == "__main__":
    main()
