import time
from typing import Any

from prometheus_client import Counter, Gauge, Histogram
from starlette.types import Message, Receive, Scope, Send

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests processed",
    ["method", "path", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ),
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Current number of in-flight HTTP requests",
    ["method"],
)


class MetricsMiddleware:
    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        status_code = 500
        start_time = time.perf_counter()

        http_requests_in_progress.labels(method=method).inc()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            duration = max(time.perf_counter() - start_time, 0.0)
            route = scope.get("route")
            route_path = route.path if route and hasattr(route, "path") else "unmatched"

            http_requests_total.labels(
                method=method,
                path=route_path,
                status_code=str(status_code),
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                path=route_path,
            ).observe(duration)

            http_requests_in_progress.labels(method=method).dec()
