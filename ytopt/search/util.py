import os
import sys
import time
import logging
from importlib import import_module
from traceback import print_exception

masterLogger = None
LOG_LEVEL = os.environ.get('ytopt_LOG_LEVEL', 'DEBUG')
LOG_LEVEL = getattr(logging, LOG_LEVEL)

class Timer:
    def __init__(self):
        self.timings = {}

    def start(self, name):
        self.timings[name] = time.time()

    def end(self, name):
        try:
            elapsed = time.time() - self.timings[name]
        except KeyError:
            print(f"TIMER error: never called timer.start({name})")
        else:
            print(f"TIMER {name}: {elapsed:.4f} seconds")
            del self.timings[name]

def conf_logger(name):
    global masterLogger
    # from mpi4py import MPI
    # comm = MPI.COMM_WORLD
    # rank = comm.Get_rank()

    if (masterLogger == None):
        masterLogger = logging.getLogger('ytopt')

        # handler = logging.FileHandler(f'ytopt-{rank}.log') # debug
        handler = logging.FileHandler('ytopt.log')
        formatter = logging.Formatter(
            '%(asctime)s|%(process)d|%(levelname)s|%(name)s:%(lineno)s] %(message)s',
            "%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        masterLogger.addHandler(handler)
        masterLogger.setLevel(LOG_LEVEL)
        masterLogger.info("\n\nLoading ytopt\n--------------")

    def log_uncaught_exceptions(exctype, value, tb):
        masterLogger.exception('Uncaught exception:',
                exc_info=(exctype,value,tb)
        )
        sys.stderr.write(f"Uncaught exception {exctype}: {value}")
        print_exception(exctype, value, tb)
    sys.excepthook = log_uncaught_exceptions
    return logging.getLogger(name)

class DelayTimer:
    def __init__(self, max_minutes=None, period=2):
        if max_minutes is None:
            max_minutes = float('inf')
        self.max_minutes = max_minutes
        self.max_seconds = max_minutes * 60.0
        self.period = period
        self.delay = True

    def pretty_time(self, seconds):
        """Format time string"""
        seconds = round(seconds, 2)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return "%02d:%02d:%02.2f" % (hours,minutes,seconds)

    def __iter__(self):
        start = time.time()
        nexttime = start + self.period
        while True:
            now = time.time()
            elapsed = now - start
            if elapsed > self.max_seconds:
                raise StopIteration
            else:
                yield self.pretty_time(elapsed)
            tosleep = nexttime - now
            if tosleep <= 0 or not self.delay:
                nexttime = now + self.period
            else:
                nexttime = now + tosleep + self.period
                time.sleep(tosleep)

def load_attr_from(str_full_module):
    """
        Args:
            - str_full_module: (str) correspond to {module_name}.{attr}
        Return: the loaded attribute from a module.
    """
    if type(str_full_module) == str:
        split_full = str_full_module.split('.')
        str_module = '.'.join(split_full[:-1])
        str_attr = split_full[-1]
        module = import_module(str_module)
        return getattr(module, str_attr)
    else:
        return str_full_module

def load_from_file(fname, attribute):
    dirname, basename = os.path.split(fname)
    sys.path.insert(0, dirname)
    module_name = os.path.splitext(basename)[0]
    module = import_module(module_name)
    return getattr(module, attribute)

def generic_loader(target, attribute):
    '''Load attribute from target module
    Args:
        - target: either path to python file, or dotted Python package name
        - attribute: name of the attribute to load from the target module
    '''
    # assert attribute in ['Problem', 'run']
    if not isinstance(target, str):
        return target
    if os.path.isfile(os.path.abspath(target)):
        target_file = os.path.abspath(target)
        return load_from_file(target_file, attribute)
    else:
        return load_attr_from(target)
