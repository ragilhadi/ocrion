"""Gunicorn configuration for OCRion API."""
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('API_PORT', '8000')}"

# Worker processes
workers = int(os.getenv('WORKERS', '4'))
worker_class = 'uvicorn.workers.UvicornWorker'
worker_connections = 1000

# Timeout settings
timeout = 120
keepalive = 5

# Process naming
proc_name = 'ocrion'

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Server mechanics
daemon = False
pidfile = None
umask = 0o007
user = None
group = None
tmp_upload_dir = None

# Max requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 100

# Graceful shutdown
graceful_timeout = 30

# SSL (if needed)
keyfile = None
certfile = None

# Preload app for faster workers (may not work with all apps)
preload_app = False

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("=" * 60)
    print("Starting OCRion API with Gunicorn")
    print(f"Workers: {workers}")
    print(f"Worker class: {worker_class}")
    print("=" * 60)


def on_exit(server):
    """Called just before exiting master process."""
    print("Shutting down OCRion API")


def worker_int(worker):
    """Called just after a worker is forked."""
    print(f"Worker {worker.pid} spawned")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    print(f"Worker {worker.pid} initialized")


def pre_exec(server):
    """Called just before a new master process is forked."""
    print("Forked child, re-executing.")


def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path}")


def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    pass


def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    print(f"Worker {worker.pid} aborted")
