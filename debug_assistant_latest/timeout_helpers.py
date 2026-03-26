import os
import queue
import threading
from functools import wraps

try:
    import timeout_decorator
except ImportError:  # pragma: no cover import-error
    timeout_decorator = None


if timeout_decorator:
    TimeoutError = timeout_decorator.TimeoutError
else:
    class TimeoutError(Exception):
        pass


def timeout(seconds):
    """Return a timeout decorator that works on both POSIX and Windows."""
    if os.name == "nt":
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                result_queue = queue.Queue(maxsize=1)

                def run_target():
                    try:
                        result_queue.put(("result", func(*args, **kwargs)))
                    except BaseException as exc:  # pragma: no cover - passthrough
                        result_queue.put(("error", exc))

                worker = threading.Thread(target=run_target, daemon=True)
                worker.start()
                worker.join(seconds)

                if worker.is_alive():
                    raise TimeoutError(f"{func.__name__} timed out after {seconds} seconds")

                try:
                    state, payload = result_queue.get_nowait()
                except queue.Empty as exc:  # pragma: no cover - defensive
                    raise RuntimeError(f"{func.__name__} finished without returning a result") from exc

                if state == "error":
                    raise payload
                return payload

            return wrapper
        return decorator

    if timeout_decorator is None:
        def decorator(func):
            return func
        return decorator

    return timeout_decorator.timeout(seconds, use_signals=True)


def withTimeout(default_value):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            owner = args[0] if args else None
            if owner is not None and hasattr(owner, "__dict__"):
                owner._last_timeout = False
            try:
                return func(*args, **kwargs)
            except TimeoutError:
                if owner is not None and hasattr(owner, "__dict__"):
                    owner._last_timeout = True
                return default_value

        return wrapper

    return decorator
