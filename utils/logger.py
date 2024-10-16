import time

# First way to enable logging in your application
# use this function as decorator for some function
# it will print duration of calculations
def logger(func):
    def wrapper(*args, **kwargs):
        if logger.log_mode:
            _start = time.time_ns()
        ret = func(*args, **kwargs)
        if logger.log_mode:
            _end = time.time_ns()
            _period = _end - _start
            if logger.log_mode == "ms":
                _period /= 1_000
            if logger.log_mode == "s":
                _period /= 1_000_000_000
            print(f"{func.__qualname__} took {_period} {logger.log_mode}")
        return ret
    return wrapper

# in main module disable or enable this parameter to control logging
# to switch_on set logger.log_mode to "s" (seconds) or "ms" (microseconds)
logger.log_mode = None

# same decorator, but you can specify logging mode directly
def parameterized_logger(log_mode):
    def _logger(func):
        def _wrapper(*args, **kwargs):
            if log_mode:
                _start = time.time_ns()
            ret = func(*args, **kwargs)
            if log_mode:
                _end = time.time_ns()
                _period = _end - _start
                if log_mode == "ms":
                    _period /= 1_000
                if log_mode == "s":
                    _period /= 1_000_000_000
                print(f"{func.__qualname__} took {_period} {log_mode}")
            return ret
        return _wrapper
    return _logger

# derive from this class to log all methods
# log_mode can be set explicitly for your class in constructor
class IndependentLoggedClass:
    def __init__(self, log_mode):
        for method in list(set(item for item in dir(self) if not item.startswith('_'))-set(vars(self).keys())):
            setattr(self, method, parameterized_logger(log_mode=log_mode)(getattr(self, method)))

# derive from this class to log all methods
# user logger.log_mode to regulate all classes, that derive from this interface
class UsualLoggedClass:
    def __init__(self):
        for method in list(set(item for item in dir(self) if not item.startswith('_'))-set(vars(self).keys())):
            setattr(self, method, logger(getattr(self, method)))

class __Test__:
    def __init__(self):
        for method in dir(self):
            if method.startswith('_Test____test'):
                getattr(self, method)()

    def __test_usecase1(self):
        class MyClass:
            def __init__(self):
                pass

            @logger
            def my_method(self):
                time.sleep(1)

        logger.log_mode = "s"
        logged_class = MyClass()
        logged_class.my_method()

    def __test_usecase2(self):
        class MyClass(IndependentLoggedClass):
            def __init__(self):
                super().__init__("s")

            def my_method(self):
                time.sleep(1)

        logged_class = MyClass()
        logged_class.my_method()

    def __test_usecase3(self):
        class MyClass(UsualLoggedClass):
            def __init__(self):
                super().__init__("s")

            def my_method(self):
                time.sleep(1)

        logger.log_mode = "s"
        logged_class = MyClass()
        logged_class.my_method()

if __name__ == "__main__":
    # run all test cases
    __Test__()
