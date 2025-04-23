from typing import Any, Tuple, Callable, Dict
from contextlib import contextmanager
import validate
import queue as QueueStore, processes as ProcessStore
import FIFOScheduler
import SchedulerParams
from stores._global import (
    global_llm_req_queue_get_message,
    global_memory_req_queue_get_message,
    global_storage_req_queue_get_message,
    global_tool_req_queue_get_message,
)

def get_default_syscall(param_name: str):
    defaults = {
        'get_llm_syscall': global_llm_req_queue_get_message,
        'get_memory_syscall': global_memory_req_queue_get_message,
        'get_storage_syscall': global_storage_req_queue_get_message,
        'get_tool_syscall': global_tool_req_queue_get_message,
    }

    return defaults.get(param_name, None)


@validate(SchedulerParams)
def useFIFOScheduler(
    params: SchedulerParams,
) -> Tuple[Callable[[], None], Callable[[], None]]:
    # Set default values if any required parameter is missing
    params.get_llm_syscall = params.get_llm_syscall or get_default_syscall('get_llm_syscall')
    params.get_memory_syscall = params.get_memory_syscall or get_default_syscall('get_memory_syscall')
    params.get_storage_syscall = params.get_storage_syscall or get_default_syscall('get_storage_syscall')
    params.get_tool_syscall = params.get_tool_syscall or get_default_syscall('get_tool_syscall')

    scheduler = FIFOScheduler(**params.model_dump())

    # Function to start the scheduler
    def startScheduler():
        scheduler.start()

    # Function to stop the scheduler
    def stopScheduler():
        scheduler.stop()

    return startScheduler, stopScheduler


@contextmanager
@validate(SchedulerParams)
def fifo_scheduler(params: SchedulerParams):
    # Set default values if any required parameter is missing
    params.get_llm_syscall = params.get_llm_syscall or get_default_syscall('get_llm_syscall')
    params.get_memory_syscall = params.get_memory_syscall or get_default_syscall('get_memory_syscall')
    params.get_storage_syscall = params.get_storage_syscall or get_default_syscall('get_storage_syscall')
    params.get_tool_syscall = params.get_tool_syscall or get_default_syscall('get_tool_syscall')

    scheduler = FIFOScheduler(**params.model_dump())

    # Start the scheduler and ensure it stops when exiting the context
    scheduler.start()
    yield
    scheduler.stop()


@validate(SchedulerParams)
def fifo_scheduler_nonblock(params: SchedulerParams):
    # Set default values if any required parameter is missing
    params.get_llm_syscall = params.get_llm_syscall or get_default_syscall('get_llm_syscall')
    params.get_memory_syscall = params.get_memory_syscall or get_default_syscall('get_memory_syscall')
    params.get_storage_syscall = params.get_storage_syscall or get_default_syscall('get_storage_syscall')
    params.get_tool_syscall = params.get_tool_syscall or get_default_syscall('get_tool_syscall')

    return FIFOScheduler(**params.model_dump())
