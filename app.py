import json
import os
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_DATA_DIR = BASE_DIR / "data"
RENDER_DATA_DIR = Path("/tmp/task-manager-data")
DATA_DIR = Path(os.environ.get("DATA_DIR", str(RENDER_DATA_DIR if os.environ.get("RENDER") == "true" else DEFAULT_DATA_DIR)))
TASKS_FILE = DATA_DIR / "tasks.json"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not TASKS_FILE.exists():
        TASKS_FILE.write_text("[]", encoding="utf-8")


def read_tasks() -> list[dict]:
    ensure_storage()
    try:
        return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        TASKS_FILE.write_text("[]", encoding="utf-8")
        return []


def write_tasks(tasks: list[dict]) -> None:
    TASKS_FILE.write_text(json.dumps(tasks, indent=2), encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskManagerHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self.serve_index()
                return
            if parsed.path == "/health":
                self.send_json(
                    HTTPStatus.OK,
                    {"status": "ok", "dataFile": str(TASKS_FILE)},
                )
                return
            if parsed.path == "/tasks":
                tasks = read_tasks()
                params = parse_qs(parsed.query)
                status = params.get("status", ["all"])[0]
                if status == "completed":
                    tasks = [task for task in tasks if task["completed"]]
                elif status == "pending":
                    tasks = [task for task in tasks if not task["completed"]]
                self.send_json(HTTPStatus.OK, {"tasks": tasks})
                return
            super().do_GET()
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Storage error: {exc}"},
            )

    def do_POST(self) -> None:
        try:
            if self.path != "/tasks":
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
                return

            payload = self.read_json_body()
            if isinstance(payload, tuple):
                status, body = payload
                self.send_json(status, body)
                return

            title = str(payload.get("title", "")).strip()
            if not title:
                self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Title is required."})
                return

            task = {
                "id": str(uuid4()),
                "title": title,
                "completed": False,
                "createdAt": utc_now(),
            }

            tasks = read_tasks()
            tasks.insert(0, task)
            write_tasks(tasks)
            self.send_json(HTTPStatus.CREATED, {"task": task, "message": "Task created."})
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Storage error: {exc}"},
            )

    def do_PATCH(self) -> None:
        try:
            task_id = self.extract_task_id()
            if not task_id:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
                return

            payload = self.read_json_body()
            if isinstance(payload, tuple):
                status, body = payload
                self.send_json(status, body)
                return

            allowed_keys = {"completed", "title"}
            if not any(key in payload for key in allowed_keys):
                self.send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Provide at least one updatable field: title or completed."},
                )
                return

            tasks = read_tasks()
            task = next((item for item in tasks if item["id"] == task_id), None)
            if task is None:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Task not found."})
                return

            if "title" in payload:
                title = str(payload.get("title", "")).strip()
                if not title:
                    self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Title cannot be empty."})
                    return
                task["title"] = title

            if "completed" in payload:
                completed = payload["completed"]
                if not isinstance(completed, bool):
                    self.send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"error": "Completed must be a boolean value."},
                    )
                    return
                task["completed"] = completed

            write_tasks(tasks)
            self.send_json(HTTPStatus.OK, {"task": task, "message": "Task updated."})
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Storage error: {exc}"},
            )

    def do_DELETE(self) -> None:
        try:
            task_id = self.extract_task_id()
            if not task_id:
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Route not found."})
                return

            tasks = read_tasks()
            updated_tasks = [task for task in tasks if task["id"] != task_id]
            if len(updated_tasks) == len(tasks):
                self.send_json(HTTPStatus.NOT_FOUND, {"error": "Task not found."})
                return

            write_tasks(updated_tasks)
            self.send_json(HTTPStatus.OK, {"message": "Task deleted."})
        except OSError as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"Storage error: {exc}"},
            )

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return HTTPStatus.BAD_REQUEST, {"error": "Request body is required."}
        try:
            raw_body = self.rfile.read(content_length)
            return json.loads(raw_body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON payload."}

    def extract_task_id(self) -> str | None:
        parts = self.path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "tasks" and parts[1]:
            return parts[1]
        return None

    def send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_index(self) -> None:
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "index.html not found."})
            return

        body = index_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run() -> None:
    ensure_storage()
    server = ThreadingHTTPServer((HOST, PORT), TaskManagerHandler)
    print(f"Task Manager running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
