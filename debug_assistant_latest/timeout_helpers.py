import os
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
    if timeout_decorator is None or os.name == "nt":
        def decorator(func):
            return func
        return decorator

    return timeout_decorator.timeout(seconds, use_signals=True)


def withTimeout(default_value):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except TimeoutError:
                return default_value

        return wrapper

    return decorator
