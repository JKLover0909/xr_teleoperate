"""Preflight port cleanup and shutdown signal handling for teleop.

A teleop session that is suspended (Ctrl+Z) or killed mid-cleanup leaves its
Vuer child process holding port 8012, which prevents the next session from
serving the XR page. These helpers detect that situation and recover from it
without touching unrelated processes.
"""
import os
import signal
import time

import psutil

import logging_mp
logger_mp = logging_mp.getLogger(__name__)

# A process is considered ours only if its command line matches one of these.
TELEOP_CMDLINE_MARKERS = ("teleop_hand_and_arm.py", "test_quest_camera.py")


def _argv(proc):
    try:
        return proc.cmdline()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def _cmdline(proc):
    return " ".join(_argv(proc))


def _runs_teleop_script(proc):
    """True if proc was launched as `python .../teleop_hand_and_arm.py ...`.

    Matching whole argv entries rather than a substring of the joined command
    line keeps a shell that merely mentions the script from being mistaken for
    the script itself.
    """
    return any(os.path.basename(arg) in TELEOP_CMDLINE_MARKERS for arg in _argv(proc))


def _is_teleop_process(proc):
    """True if proc is a teleop session, or a worker forked by one."""
    if _runs_teleop_script(proc):
        return True
    # multiprocessing workers inherit argv, but a spawned helper may not; walk a
    # couple of levels up so those are still recognised as ours.
    try:
        ancestors = proc.parents()[:2]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
    return any(_runs_teleop_script(ancestor) for ancestor in ancestors)


def _listeners_on_port(port):
    """Return the processes currently listening on port."""
    procs = {}
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, PermissionError):
        logger_mp.warning(f"[ProcessGuard] Cannot inspect sockets; skipping port {port} preflight.")
        return []
    for conn in connections:
        if conn.status != psutil.CONN_LISTEN or conn.laddr.port != port or conn.pid is None:
            continue
        try:
            procs[conn.pid] = psutil.Process(conn.pid)
        except psutil.NoSuchProcess:
            continue
    return list(procs.values())


def _terminate(proc):
    """Resume (in case it is suspended), then terminate, then kill if needed."""
    pid = proc.pid
    try:
        proc.send_signal(signal.SIGCONT)  # a stopped process cannot handle SIGTERM
        proc.terminate()
        proc.wait(timeout=3)
        logger_mp.info(f"[ProcessGuard] Stale teleop process {pid} terminated.")
        return True
    except psutil.NoSuchProcess:
        return True
    except psutil.TimeoutExpired:
        pass
    except psutil.AccessDenied:
        logger_mp.error(f"[ProcessGuard] No permission to stop process {pid}.")
        return False

    try:
        proc.kill()
        proc.wait(timeout=3)
        logger_mp.info(f"[ProcessGuard] Stale teleop process {pid} killed.")
        return True
    except psutil.NoSuchProcess:
        return True
    except (psutil.TimeoutExpired, psutil.AccessDenied):
        logger_mp.error(f"[ProcessGuard] Failed to stop process {pid}.")
        return False


def _orphaned_teleop_processes():
    """Teleop processes left over from an earlier run, reparented to init/systemd.

    A session that exits without reaping its multiprocessing workers leaves them
    running; they hold DDS subscriptions and shared memory even when they are no
    longer bound to the Vuer port.
    """
    mine = {os.getpid()}
    try:
        mine.update(child.pid for child in psutil.Process().children(recursive=True))
    except psutil.NoSuchProcess:
        pass

    orphans = []
    for proc in psutil.process_iter(["pid", "ppid"]):
        if proc.pid in mine or not _runs_teleop_script(proc):
            continue
        try:
            # ppid 1 (init) or the user's systemd instance means the original
            # session is gone; a live session still owns its children.
            parent = proc.parent()
            if parent is None or parent.pid == 1 or "systemd" in parent.name():
                orphans.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return orphans


def ensure_port_free(port, timeout=5.0):
    """Clear leftovers from a previous teleop session.

    Frees `port` and reaps orphaned teleop workers. Only processes belonging to
    a teleop session are stopped; anything else raises, so an unrelated service
    is never killed by surprise.
    """
    listeners = [p for p in _listeners_on_port(port) if p.pid != os.getpid()]

    foreign = [p for p in listeners if not _is_teleop_process(p)]
    if foreign:
        details = ", ".join(f"pid={p.pid} ({_cmdline(p) or p.name()})" for p in foreign)
        raise RuntimeError(
            f"Port {port} is held by a non-teleop process: {details}. "
            f"Stop it manually, then rerun."
        )

    for proc in listeners:
        logger_mp.warning(
            f"[ProcessGuard] Port {port} still held by stale teleop process {proc.pid}; cleaning up."
        )
        _terminate(proc)

    for proc in _orphaned_teleop_processes():
        logger_mp.warning(f"[ProcessGuard] Reaping orphaned teleop process {proc.pid}.")
        _terminate(proc)

    if not listeners:
        return

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _listeners_on_port(port):
            logger_mp.info(f"[ProcessGuard] Port {port} is free.")
            return
        time.sleep(0.2)

    raise RuntimeError(f"Port {port} is still in use after cleanup. Stop the old session manually.")


def install_shutdown_handlers(on_stop):
    """Route SIGINT/SIGTERM to on_stop() so cleanup runs to completion.

    Without this, Ctrl+C raises KeyboardInterrupt wherever the main thread
    happens to be -- including inside the cleanup block itself, which is how
    the Vuer server ends up orphaned and still bound to its port.
    """
    state = {"requested": False}

    def handler(signum, _frame):
        if state["requested"]:
            logger_mp.warning("[ProcessGuard] Shutdown already in progress; ignoring signal.")
            return
        state["requested"] = True
        logger_mp.info(f"[ProcessGuard] Signal {signal.Signals(signum).name} received; shutting down.")
        on_stop()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
