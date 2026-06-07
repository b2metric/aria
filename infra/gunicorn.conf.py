# Gunicorn configuration for ARIA production deployment
# https://docs.gunicorn.org/en/stable/settings.html

import multiprocessing
import os

# ── Server Socket ─────────────────────────────────────────────────────
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# ── Worker Processes ──────────────────────────────────────────────────
# Rule of thumb: 2-4 workers per core
# For I/O bound apps (like ARIA with DB/LLM calls), more workers help
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 10000  # Restart workers after N requests (memory leak prevention)
max_requests_jitter = 1000  # Random jitter to avoid thundering herd

# ── Timeouts ──────────────────────────────────────────────────────────
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))  # Worker timeout (LLM calls can be slow)
graceful_timeout = 30  # Graceful shutdown timeout
keepalive = 5  # Keepalive connections

# ── Server Mechanics ──────────────────────────────────────────────────
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# ── Logging ───────────────────────────────────────────────────────────
errorlog = "-"  # stderr
accesslog = "-"  # stdout
loglevel = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ── Process Naming ────────────────────────────────────────────────────
proc_name = "aria-backend"

# ── SSL (if terminating at Gunicorn, not recommended - use Traefik) ───
keyfile = None
certfile = None

# ── Server Hooks ──────────────────────────────────────────────────────
def on_starting(server):
    """Called just before the master process is initialized."""
    pass

def on_reload(server):
    """Called when SIGHUP is received."""
    pass

def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    pass

def worker_abort(worker):
    """Called when a worker receives SIGABRT (timeout)."""
    pass

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    pass

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    pass

def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    pass

def on_exit(server):
    """Called just before exiting Gunicorn."""
    pass
