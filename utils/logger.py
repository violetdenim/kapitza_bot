import time
log_mode = None

def logger(func):
    def wrapper(*args, **kwargs):
        global log_mode
        if log_mode:
            _start = time.time_ns()
        ret = func(*args, **kwargs)
        if log_mode:
            _end = time.time_ns()
            _period = _end - _start
            if log_mode == "ms":
                _period /= 1_000
            if log_mode == "s":
                _period /= 1_000_000
            print(f"{func.__name__} took {_period} {log_mode}")
        return ret
    return wrapper
