"""A visual editor for the wiring of the keyplate.

    python scripts/wiring_editor.py [--port 8765] [--no-browser] [--file path/to/wiring.yaml]

The script starts a small server on this computer and opens the editor in the browser.
The editor reads and writes ergogen/wave.wiring.yaml. The checks are those of `duality_wave.wiring.check`.
Before the editor writes the file, it copies the old file to build/wave.wiring.backup.yaml.
Press Ctrl+C in the terminal to stop the server.
"""

import argparse
import json
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from duality_wave.cli.common import case_context
from duality_wave.paths import WIRING_FILE
from duality_wave.wiring.editor import Editor, EditorError
from duality_wave.wiring.plan import WiringFileError

PAGE = Path(__file__).with_name("wiring_editor.html")
# the editor sends this header, so a page from another site cannot write the file
GUARD = "X-Wiring-Editor"


def make_handler(editor: Editor, port: int):
    lock = threading.Lock()
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:
            pass

        def reply(self, status: int, body: bytes, kind: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def json(self, data, status: int = 200) -> None:
            self.reply(status, json.dumps(data).encode())

        def allowed(self) -> bool:
            return self.headers.get("Host") in hosts

        def do_GET(self) -> None:
            if not self.allowed():
                return self.json({"error": "wrong host"}, 403)
            route, _, query = self.path.partition("?")
            try:
                if route in ("/", "/index.html"):
                    return self.reply(200, PAGE.read_bytes(), "text/html")
                if not self.headers.get(GUARD):
                    return self.json({"error": "missing header"}, 403)
                with lock:
                    if route == "/api/document":
                        editor.reload()
                        return self.json({"document": editor.document(), "geometry": {s: editor.geometry(s) for s in ("left", "right")}})
            except (EditorError, WiringFileError) as error:
                return self.json({"error": str(error)}, 400)
            except Exception as error:  # the browser shows the message
                traceback.print_exc()
                return self.json({"error": f"{type(error).__name__}: {error}"}, 500)
            self.json({"error": "not found"}, 404)

        def do_POST(self) -> None:
            if not self.allowed() or not self.headers.get(GUARD):
                return self.json({"error": "forbidden"}, 403)
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length) or b"{}")
                with lock:
                    if self.path == "/api/analyze":
                        return self.json(editor.analyze(data["side"], data["state"], bool(data.get("fast"))))
                    if self.path == "/api/tidy":
                        paths, removed = editor.tidy(data["state"])
                        return self.json({"paths": paths, "removed": removed})
                    if self.path == "/api/save":
                        return self.json({"document": editor.save(data["state"])})
            except (EditorError, WiringFileError) as error:
                return self.json({"error": str(error)}, 400)
            except Exception as error:
                traceback.print_exc()
                return self.json({"error": f"{type(error).__name__}: {error}"}, 500)
            self.json({"error": "not found"}, 404)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--file", type=Path, default=WIRING_FILE, help="the wiring file (default: ergogen/wave.wiring.yaml)")
    args = parser.parse_args()

    editor = Editor(case_context(), args.file)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(editor, args.port))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"wiring editor at {url} (Ctrl+C stops it)")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
