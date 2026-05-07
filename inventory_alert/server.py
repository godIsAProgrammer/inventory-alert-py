from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os

from .router import InventoryRouter


class RequestHandler(BaseHTTPRequestHandler):
    router = InventoryRouter()

    def do_GET(self) -> None:  # noqa: N802 - http.server 使用固定方法名
        self.router.handle(self)

    def do_POST(self) -> None:  # noqa: N802
        self.router.handle(self)

    def do_PATCH(self) -> None:  # noqa: N802
        self.router.handle(self)

    def log_message(self, format: str, *args) -> None:
        # 默认访问日志足够用于本地排查，保持一行输出，方便 Docker logs 查看。
        print("%s - %s" % (self.address_string(), format % args))


def main() -> None:
    port = int(os.environ.get("PORT", "8791"))
    server = ThreadingHTTPServer(("0.0.0.0", port), RequestHandler)
    print(f"inventory-alert-py listening on {port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
