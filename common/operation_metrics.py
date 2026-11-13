"""Timing only: no retries, waits, argument capture or outcome changes."""
from functools import wraps
from time import perf_counter

OPERATIONS={}


def timed_operation(function):
    @wraps(function)
    def measured(*args,**kwargs):
        started=perf_counter()
        succeeded=False
        try:
            result=function(*args,**kwargs)
            succeeded=True
            return result
        finally:
            duration=perf_counter()-started
            key=function.__module__+'.'+function.__qualname__
            record=OPERATIONS.setdefault(key,{'count':0,'seconds':0.0,'max_seconds':0.0,'exceptions':0})
            record['count']+=1;record['seconds']+=duration
            record['max_seconds']=max(record['max_seconds'],duration)
            record['exceptions']+=not succeeded
    return measured
