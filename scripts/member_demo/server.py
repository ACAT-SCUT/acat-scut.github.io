"""Run with: python -B scripts/member_demo/server.py --port 8766"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
import uuid

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from member_demo.core import DemoError, ROOT, Store
from member_demo.render import render_members

STATIC = Path(__file__).resolve().parent / "static"


def make_handler(store):
    class Handler(BaseHTTPRequestHandler):
        server_version = "MemberDemo/1.0"

        def log_message(self, format, *args):
            pass  # Local application details are not printed into shared logs.

        def send(self, body, content_type="application/json; charset=utf-8", status=200):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False)
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; frame-src 'self'; frame-ancestors 'self'; form-action 'self'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.valid_host():
                self.send({"error": "请通过提供的本机地址打开演示"}, status=403)
                return
            path = urlparse(self.path).path
            try:
                if path == "/api/state":
                    self.send(store.public_state())
                elif path == "/members":
                    self.send(render_members(store.read()), "text/html; charset=utf-8")
                elif path in ("/", "/app.js", "/style.css"):
                    filename, kind = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}[path]
                    self.send((STATIC / filename).read_bytes(), kind + "; charset=utf-8")
                elif path.startswith("/exports/"):
                    filename = path.removeprefix("/exports/")
                    if not filename.endswith(".csv") or "/" in filename or "\\" in filename or ".." in filename:
                        raise DemoError("文件路径不正确")
                    self.send((store.directory / "exports" / filename).read_bytes(), "text/plain; charset=utf-8")
                else:
                    self.send({"error": "未找到页面"}, status=404)
            except (DemoError, FileNotFoundError) as error:
                self.send({"error": str(error) if isinstance(error, DemoError) else "未找到文件"}, status=404)

        def do_POST(self):
            expected_origin = f"http://127.0.0.1:{self.server.server_port}"
            if not self.valid_host() or self.headers.get("Origin", expected_origin) != expected_origin:
                self.send({"error": "仅接受当前本机页面的操作"}, status=403)
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.send({"error": "请求格式须为JSON"}, status=415)
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    raise DemoError("请求内容过大或为空")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise DemoError("请求须为对象")
                route = urlparse(self.path).path
                if route == "/api/submit":
                    result = store.submit(payload)
                elif route == "/api/review":
                    result = store.review(payload.get("requestId"), payload.get("decision"), payload.get("note", ""), payload.get("target"))
                elif route == "/api/preview":
                    result = store.preview(payload.get("requestId"))
                elif route == "/api/apply":
                    result = store.apply(payload.get("requestId"), payload.get("token"))
                elif route == "/api/reset":
                    store.reset(payload.get("confirmed"))
                    result = {"reset": True}
                elif route == "/api/export":
                    reviewed = payload.get("reviewed") is True
                    name = ("reviews-" if reviewed else "requests-") + uuid.uuid4().hex[:10] + ".csv"
                    directory = store.directory / "exports"
                    directory.mkdir(exist_ok=True)
                    (directory / name).write_text(store.export_csv(reviewed), encoding="utf-8", newline="\n")
                    result = {"path": (directory / name).relative_to(ROOT).as_posix(), "url": "/exports/" + name}
                else:
                    self.send({"error": "未找到操作"}, status=404)
                    return
                self.send(result)
            except (DemoError, ValueError, TypeError, KeyError, StopIteration) as error:
                message = str(error) if isinstance(error, DemoError) else "请求格式不正确，请刷新后重试"
                self.send({"error": message}, status=400)
            except OSError:
                self.send({"error": "保存失败，原数据未被替换。请检查文件占用和磁盘空间，再重试。"}, status=500)

    return Handler


def create_server(directory, port=8766):
    return ThreadingHTTPServer(("127.0.0.1", port), make_handler(Store(directory)))


def main():
    parser = argparse.ArgumentParser(description="仅使用虚构资料的本机成员维护演示")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--data-dir", type=Path, default=ROOT / ".local/member-demo")
    args = parser.parse_args()
    try:
        server = create_server(args.data_dir, args.port)
    except (OSError, DemoError) as error:
        parser.exit(1, str(error) + "\n")
    print(f"成员维护演示：http://127.0.0.1:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
