# api/webhook.py
#
# Vercel Python Serverless Function.
# Telegram sends every update as an HTTP POST to this endpoint.
#
# Vercel Python runtime expects a top-level function:
#
#   def handler(request: BaseHTTPRequestHandler) -> None
#
# or the newer WSGI/ASGI style.  The safest, most compatible approach
# for Vercel is the HTTP handler below.

from http.server import BaseHTTPRequestHandler
import json
import asyncio
import sys
import os
from pathlib import Path

# ── Make project root importable ─────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from bot import create_application          # noqa: E402  (after sys.path tweak)
from telegram import Update                 # noqa: E402

# ── Module-level singleton (reused across warm invocations) ──────────────────
_app = None


def _get_app():
    global _app
    if _app is None:
        _app = create_application()
    return _app


async def _handle_update(body: dict) -> None:
    app = _get_app()
    # Initialize once; safe to call multiple times (PTB is idempotent here)
    if not app._initialized:          # noqa: SLF001
        await app.initialize()
    update = Update.de_json(data=body, bot=app.bot)
    await app.process_update(update)


# ── Vercel handler class ──────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    """
    Vercel calls this class for every incoming HTTP request.
    Only POST / is used (Telegram webhook).
    """

    def log_message(self, format, *args):  # silence default access logs
        pass

    def do_GET(self):
        self._respond(200, {"ok": True, "status": "Telegram bot webhook is live."})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            body = json.loads(raw)
        except Exception as e:
            self._respond(400, {"ok": False, "error": f"Bad JSON: {e}"})
            return

        try:
            asyncio.run(_handle_update(body))
        except Exception as e:
            # Log but always return 200 — otherwise Telegram retries forever
            print(f"[webhook] ERROR processing update: {e}", file=sys.stderr)

        # Always acknowledge to Telegram
        self._respond(200, {"ok": True})

    def _respond(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
 