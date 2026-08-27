"""
Clone-bot supervisor.

The main bot can create unlimited *live* clones: each clone runs the exact same
handler pipeline as the main bot (same modules, same database, same features)
but polls Telegram with its own bot token. Clones do not need to be deployed —
they run as background threads inside the same process as the main bot.

Status model (stored in the ``bot_instances`` table):

    active     — the application exists and is polling updates (live online).
    paused     — the application exists but polling is stopped; can be resumed.
    disabled   — the app was shut down; must be enabled (or started) first.
"""
import asyncio
import logging
import threading
import time

from telegram.ext import Application

from config import Config
from database import db

logger = logging.getLogger(__name__)

# registry: instance_id -> running-thread info dict
_REGISTRY = {}
_REGISTRY_LOCK = threading.RLock()
SUPERVISOR_STARTED = False


class CloneHandle:
    """Runtime handle for one running clone bot."""

    def __init__(self, instance, thread: threading.Thread):
        self.instance = instance
        self.thread = thread
        self.app = None            # set once the application is built
        self.stop_event = threading.Event()
        self.started_at = time.time()


def _set_env_for(token: str, username: str):
    """Point the process-wide Config at a specific clone for THIS thread."""
    Config.configure_bot_environment(token, username)


def _wait_stop_signal(app, stop_event: threading.Event):
    """Run inside the clone's loop: stop the application when requested."""
    loop = asyncio.get_running_loop()

    def _check():
        if stop_event.is_set():
            # Stops the loop gracefully (see Application.stop_running doc).
            app.stop_running()
            return
        loop.call_later(0.5, _check)

    loop.call_later(0.5, _check)


def _run_clone_loop(instance_id: int):
    """Target of a clone thread: build an application and run it until stopped.

    Runs inside its own thread; each clone therefore has its own asyncio event
    loop (Python 3.13 does not auto-create one in non-main threads).
    """
    thread_name = f"clone-{instance_id}"
    old_name = threading.current_thread().name
    threading.current_thread().name = thread_name

    handle = None
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        instance = db.get_bot_instance_by_id(instance_id)
        if instance is None:
            logger.error("[%s] instance missing; exiting thread", thread_name)
            return

        _set_env_for(instance.token, instance.username)

        from bot import build_application, Update

        logger.info("[%s] starting clone %s (@%s) ...", thread_name, instance.id, instance.username)
        app = build_application(token=instance.token, start_clones=False)

        with _REGISTRY_LOCK:
            handle = _REGISTRY.get(instance_id)
            if handle is not None:
                handle.app = app

        # Set status to active once the application is up.
        current = db.get_bot_instance_by_id(instance_id)
        if current is not None:
            db.set_bot_status(instance_id, 'active')

        # Schedule a periodic check that stops the app when requested.
        if handle is not None:
            loop.call_soon(lambda: _wait_stop_signal(app, handle.stop_event))

        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False,
            # Signal handlers only work in the main thread; lifecycle is
            # managed via handle.stop_event / overwatch above.
            stop_signals=None,
        )
    except Exception as e:
        logger.error("[%s] clone loop crashed: %s", thread_name, e)
        if "rejected by the server" in str(e):
            # Token revoked/invalid: permanently disable so the owner can
            # re-issue a valid token or remove this clone.
            try:
                db.set_bot_status(instance_id, 'disabled')
            except Exception:
                pass
    finally:
        # If the loop exits unexpectedly, mark as paused so the owner can
        # resume without re-enabling. Explicit stop/disable already set the DB
        # status before the thread ended, so leave it untouched.
        try:
            current = db.get_bot_instance_by_id(instance_id)
            if current is not None and current.status == 'active':
                db.set_bot_status(instance_id, 'paused')
        except Exception:
            pass
        with _REGISTRY_LOCK:
            _REGISTRY.pop(instance_id, None)
        try:
            # Close the loop (pending tasks, if any, are cancelled by PTB's
            # shutdown sequence).
            if not loop.is_closed():
                loop.close()
        except Exception:
            pass
        threading.current_thread().name = old_name
        logger.info("[%s] clone thread finished", thread_name)


def _is_main_token(token: str) -> bool:
    """True if the token belongs to the main bot."""
    return bool(token) and token == Config.BOT_TOKEN


def start_clone(instance_id: int) -> bool:
    """Start (or restart) a clone thread for the given instance. Returns True on success."""
    with _REGISTRY_LOCK:
        if instance_id in _REGISTRY and _REGISTRY[instance_id].thread.is_alive():
            return False  # already running
        instance = db.get_bot_instance_by_id(instance_id)
        if instance is None:
            return False
        if _is_main_token(instance.token):
            return False
        thread = threading.Thread(
            target=_run_clone_loop,
            args=(instance_id,),
            name=f"clone-{instance_id}",
            daemon=True,
        )
        thread.start()
        _REGISTRY[instance_id] = CloneHandle(instance, thread)
        logger.info("Started clone thread for instance %s (@%s)", instance_id, instance.username)
        return True


def stop_clone(instance_id: int, mark: str = 'paused', wait: float = 5.0) -> bool:
    """Gracefully stop a running clone's application.

    ``mark`` is the status to persist: 'paused' (default) or 'disabled'.
    Signals the clone's event loop to stop the application, then waits up to
    ``wait`` seconds (bounded) for the thread to finish so that immediate
    start/stop sequences are deterministic.
    """
    with _REGISTRY_LOCK:
        handle = _REGISTRY.get(instance_id)
    if handle is None:
        return False

    instance = db.get_bot_instance_by_id(instance_id)
    if instance is not None:
        db.set_bot_status(instance_id, mark)
    handle.stop_event.set()
    if wait and handle.thread.is_alive():
        handle.thread.join(wait)
    return True


def _shutdown_all():
    """Stop every running clone (used at tests/interpreter-teardown)."""
    with _REGISTRY_LOCK:
        ids = list(_REGISTRY.keys())
    for iid in ids:
        stop_clone(iid, mark='paused')
    return ids


def is_clone_running(instance_id: int) -> bool:
    """True if the clone thread is alive in this process."""
    with _REGISTRY_LOCK:
        handle = _REGISTRY.get(instance_id)
        return handle is not None and handle.thread.is_alive()


def get_running_clones():
    """Return list of (instance_id, start_time) for running clones."""
    with _REGISTRY_LOCK:
        return [(iid, h.started_at) for iid, h in _REGISTRY.items() if h.thread.is_alive()]


def start_clone_supervisor():
    """Auto-start every clone marked 'active' (used at boot).

    Safe to call multiple times; non-re-entrant.
    """
    global SUPERVISOR_STARTED
    with _REGISTRY_LOCK:
        if SUPERVISOR_STARTED:
            return
        rows = db.get_bot_instances(only_known=True)
        for row in rows:
            if row.status == 'active' and not is_clone_running(row.id):
                try:
                    start_clone(row.id)
                except Exception as e:
                    logger.error("Failed to auto-start clone %s: %s", row.id, e)
        SUPERVISOR_STARTED = True
        logger.info("Clone supervisor started with %d registered clone(s)", len(rows))


def set_clone_status(instance_id: int, status: str) -> tuple:
    """
    Apply a lifecycle action to a clone. Returns (ok, message).

    status:
        start   -> create the app & begin polling (status = active)
        stop    -> stop polling, app remains (status = paused)
        enable  -> allow the clone to run (status = disabled -> active, starts)
        disable -> stop it permanently (status = disabled)
        resume  -> exactly like start (used after a stop/pause)
        pause   -> temporarily stop polling (status = paused)
    """
    instance = db.get_bot_instance_by_id(instance_id)
    if instance is None:
        return False, "clone not found"

    if _is_main_token(instance.token):
        return False, "the main bot cannot be managed as a clone"

    if status in ('start', 'enable', 'resume'):
        if is_clone_running(instance_id):
            db.set_bot_status(instance_id, 'active')
            return True, "already running"
        db.set_bot_status(instance_id, 'active')
        ok = start_clone(instance_id)
        if ok:
            return True, "started"
        db.set_bot_status(instance_id, 'paused')
        return False, "could not start (is it already running?)"

    if status in ('stop', 'disable', 'pause'):
        was_running = is_clone_running(instance_id)
        mark = 'disabled' if status == 'disable' else 'paused'
        if was_running:
            stop_clone(instance_id, mark=mark)
        else:
            db.set_bot_status(instance_id, mark)
        return True, f"{status}ed"

    return False, f"unknown action: {status}"


# ---------------------------------------------------------------------------
# Test helpers (not used by production code)
# ---------------------------------------------------------------------------
def _registry_len():
    with _REGISTRY_LOCK:
        return len(_REGISTRY)


def _reset_registry():
    global SUPERVISOR_STARTED
    with _REGISTRY_LOCK:
        for iid in list(_REGISTRY.keys()):
            _REGISTRY.pop(iid, None)
        SUPERVISOR_STARTED = False