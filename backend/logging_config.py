import sys
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import json
import time
from datetime import datetime, timezone
import contextvars
from .config import settings
import logfire

# this is handled for each unique req using set/get
request_id_ctx = contextvars.ContextVar("X-Request-ID", default=None)
# name is just label, default value is none
correlation_id_ctx = contextvars.ContextVar("X-Correlation-ID", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            # record.created is unix based
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            # record.msg -> log created for %s
            # record.args -> user
            # record.getMessage combines both -> log created for user.
            # if extra used in logging, then python creates record.extra_data
            "env": "production" if settings().is_prod else "dev",
            # always better to use enum class here too
        }
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            payload.update(record.extra_data)
        for key in ("request_id", "correlation_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
                # if i have used record.key it would literally looks for record."key"
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
            # format excetion writes in readable format
        return json.dumps(payload, default=str)
        # like exception value is not json serialazable so write default=str


class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get()
        record.correlation_id = correlation_id_ctx.get()
        return True


logger = logging.getLogger("backend")
logger.addFilter(ContextFilter())
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setFormatter(JsonFormatter())
logger.addHandler(logfire.LogfireLoggingHandler())  # use stream_handler in prod
logger.propagate = False
logger.setLevel(logging.INFO if settings().is_prod else logging.DEBUG)
# this line if not used, inherits from parents


# wraps all http req
# browser-> middleware -> dispatch() -> call_next()  calls route, returns response
# correlation id header added to response -> middleware return response send to client
class RouteMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        # in larger systems there may already be a correlation ID generated upstream
        # say be cloudfare, we can configure to send with this header name instead
        # request id is our app lifecycle

        req_token = request_id_ctx.set(str(uuid.uuid4()))
        corr_token = correlation_id_ctx.set(correlation_id)

        try:
            # calls route endpoint or next middleware
            response: Response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000
            self._log_request(request, response.status_code, process_time, error=False)
            # can set requestid here in headers of response too.
            return response  # python does not have block scope like c++ for try/except
        # only if try actually runs.
        except Exception:
            # http codes raised using HTTPException dont enter here
            process_time = (time.perf_counter() - start_time) * 1000  # returns in s
            self._log_request(request, 500, process_time, error=True)
            raise
        finally:
            # Prevent state leakage between recycled event loop tasks
            request_id_ctx.reset(req_token)
            correlation_id_ctx.reset(corr_token)

    def _log_request(
        self,
        request: Request,
        status_code: int,
        duration_ms: float,
        error: bool,
    ):
        log_payload = {
            "http_method": request.method,
            "path": request.url.path,
            "status_code": status_code,  # for errors ->500
            "duration_ms": round(duration_ms, 2),
            "client_ip": request.client.host if request.client else "unknown",
        }

        if error:
            logger.error("request_failed", extra={"extra_data": log_payload})
        else:
            logger.info("request_completed", extra={"extra_data": log_payload})


"""



request.state.correlation_id = correlation_id
this state only lives for this req lifetime only
say in our code, we call external db, then a new req is formed with req.state for db
when db recieves this req.


              logger.error(...) for any level ->LogRecord
                    │
                    ▼
                ContextFilter
                    │
                    ▼
                JsonFormatter
                     │
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
 Console Handler  File Handler  HTTP Handler
        │            │             │
     stdout       app.log(using queue)       db service say using queue

root handler -> directory.module handler
if logger have no handler propogates to root 
even if have handler propogtes to root, if logger.propogate = True (default)
if there is handler for logger, but some property is not set, inherits parents.

filter is add to logger.
formatter is added to handler which is added to logger.

to make sure each logger in a file gives in appropriate format,
use struct log
third-party logging library built on top of Python's logging.
Instead of

logger.info(
    f"Order {order.id} placed for ₹{amount}"
)

we write

log.info(
    "order_placed",
    order_id=123,
    amount=250,
)


to track anything using ids, newer way is
traceparent
It's a standardized HTTP header defined by the W3C Trace Context specification.
Its a standard so need to manally add in header not done by http
also better to use it since, all vendors say cloudfare,nignx understand this
and add this header, even client forntend can sometimes send this, 
using an observability SDK like OpenTelemetry

Example:

traceparent:
00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

Breaking it down:

00
│
├── Version

4bf92f3577b34da6a3ce929d0e0e4736
│
├── Trace ID -> like correlation

00f067aa0ba902b7
│
├── Parent Span ID -> like request id

01
│
└── Trace flags -> just tell to either read this or not


Libraries such as OpenTelemetry automatically:

read traceparent from incoming requests,
create new span IDs,
propagate the header when making outbound HTTP calls,
attach the current trace_id and span_id to your logs.

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument() -> now add to all http downward req 

while datadog 
> automatically instruments supported libraries such as:
FastAPI
Starlette
Django
Flask
requests
httpx
SQLAlchemy
psycopg
Redis
> it req zero code to add in app
just run app with -> uv run ddtrace-run python main.py



whatever written in routemiddleware is handled by these tools.
these rools add in root logger by default.






"""
