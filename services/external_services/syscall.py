import time
import logging
import threading
import random
from typing import Any, Dict

import Syscall
import LLMSyscall
import StorageSyscall
import ToolSyscall
from cerebrum.llm.communication import LLMQuery
from cerebrum.memory.communication import MemoryQuery
from cerebrum.storage.communication import StorageQuery
from cerebrum.tool.communication import ToolQuery

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    filename="syscall_operations.log",
)
log = logging.getLogger(__name__)

MAX_RETRY_ATTEMPTS = 5
RETRY_DELAY = 2  # seconds
CONCURRENCY_LIMIT = 10  # Maximum concurrent syscalls

class SyscallExecutor:
    """
    This class is responsible for managing and executing syscalls related to storage, memory, tools, and LLMs.
    It supports retries, concurrent execution, and detailed logging.
    """

    def __init__(self):
        self.active_syscalls = {}
        self.lock = threading.Lock()

    def _retry_on_failure(self, func, *args, retries=MAX_RETRY_ATTEMPTS, delay=RETRY_DELAY, **kwargs):
        """
        Retries a function call if it fails, with exponential backoff.
        """
        attempt = 0
        while attempt < retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f"Attempt {attempt + 1} failed: {str(e)}")
                attempt += 1
                if attempt < retries:
                    log.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    log.error(f"Max retry attempts reached. Raising error: {str(e)}")
                    raise

    def _log_syscall_info(self, syscall_type: str, agent_name: str, status: str):
        """
        Logs detailed information about the status of the syscall.
        """
        log.info(f"Syscall: {syscall_type} - Agent: {agent_name} - Status: {status}")

    def _execute_syscall(self, syscall_type: str, agent_name: str, query: Any) -> Dict[str, Any]:
        """
        Executes a syscall based on its type (storage, memory, tool, or llm).
        """
        if syscall_type == "storage":
            return self._storage_syscall_exec(agent_name, query)
        elif syscall_type == "memory":
            return self._mem_syscall_exec(agent_name, query)
        elif syscall_type == "tool":
            return self._tool_syscall_exec(agent_name, query)
        elif syscall_type == "llm":
            return self._llm_syscall_exec(agent_name, query)
        else:
            raise ValueError(f"Unknown syscall type: {syscall_type}")

    def _storage_syscall_exec(self, agent_name: str, query: StorageQuery) -> Dict[str, Any]:
        """
        Executes the storage syscall and logs the results.
        """
        syscall = StorageSyscall(agent_name, query)
        return self._syscall_execution_workflow(syscall, agent_name, "storage")

    def _mem_syscall_exec(self, agent_name: str, query: MemoryQuery) -> Dict[str, Any]:
        """
        Executes the memory syscall and logs the results.
        """
        syscall = Syscall(agent_name, query)
        return self._syscall_execution_workflow(syscall, agent_name, "memory")

    def _tool_syscall_exec(self, agent_name: str, tool_calls: ToolQuery) -> Dict[str, Any]:
        """
        Executes the tool syscall and logs the results.
        """
        syscall = ToolSyscall(agent_name, tool_calls)
        return self._syscall_execution_workflow(syscall, agent_name, "tool")

    def _llm_syscall_exec(self, agent_name: str, query: LLMQuery) -> Dict[str, Any]:
        """
        Executes the LLM syscall and logs the results.
        """
        syscall = LLMSyscall(agent_name, query)
        return self._syscall_execution_workflow(syscall, agent_name, "llm")

    def _syscall_execution_workflow(self, syscall, agent_name: str, syscall_type: str) -> Dict[str, Any]:
        """
        Executes a syscall, logs timing and status, and retries if necessary.
        """
        try:
            # Log before starting
            self._log_syscall_info(syscall_type, agent_name, "starting")

            syscall.set_status("active")
            syscall.start()

            # Wait for the syscall to finish
            syscall.join()

            # Log after completion
            response = syscall.get_response()
            self._log_syscall_info(syscall_type, agent_name, "completed")

            # Log times
            start_time = syscall.get_start_time()
            end_time = syscall.get_end_time()
            waiting_time = start_time - syscall.get_created_time()
            turnaround_time = end_time - syscall.get_created_time()

            log.info(f"Syscall {syscall_type} - Start Time: {start_time}, End Time: {end_time}")
            log.info(f"Waiting Time: {waiting_time}, Turnaround Time: {turnaround_time}")

            return {
                "response": response,
                "start_time": start_time,
                "end_time": end_time,
                "waiting_time": waiting_time,
                "turnaround_time": turnaround_time,
            }

        except Exception as e:
            log.error(f"Error during {syscall_type} syscall execution for {agent_name}: {str(e)}")
            return {"error": str(e)}

    def handle_concurrent_requests(self, syscall_type: str, agent_name: str, query: Any):
        """
        Handles concurrent syscalls with a maximum limit.
        """
        with self.lock:
            if len(self.active_syscalls) >= CONCURRENCY_LIMIT:
                log.warning("Max concurrency limit reached. Please try again later.")
                return {"error": "Concurrency limit reached"}

            # Generate unique task ID for tracking
            task_id = random.randint(1000, 9999)
            self.active_syscalls[task_id] = {"status": "pending", "query": query}

        try:
            result = self._retry_on_failure(self._execute_syscall, syscall_type, agent_name, query)
            with self.lock:
                self.active_syscalls[task_id]["status"] = "completed"
                self.active_syscalls[task_id]["result"] = result
            return result
        except Exception as e:
            with self.lock:
                self.active_syscalls[task_id]["status"] = "failed"
                self.active_syscalls[task_id]["error"] = str(e)
            return {"error": str(e)}

    def get_active_syscalls(self):
        """
        Returns the status of active syscalls.
        """
        with self.lock:
            return self.active_syscalls


class SysCallWrapper:
    """
    This class wraps the syscall executor for each type of agent and query.
    """

    def __init__(self):
        self.syscall_executor = SyscallExecutor()

    def send_request(self, agent_name: str, query: Any) -> Dict[str, Any]:
        """
        Dispatches requests to the appropriate syscall executor based on the query type.
        """
        if isinstance(query, LLMQuery):
            return self.syscall_executor.handle_concurrent_requests("llm", agent_name, query)
        elif isinstance(query, ToolQuery):
            return self.syscall_executor.handle_concurrent_requests("tool", agent_name, query)
        elif isinstance(query, MemoryQuery):
            return self.syscall_executor.handle_concurrent_requests("memory", agent_name, query)
        elif isinstance(query, StorageQuery):
            return self.syscall_executor.handle_concurrent_requests("storage", agent_name, query)
        else:
            return {"error": "Unsupported query type"}

    def get_status(self) -> Dict[int, Dict[str, Any]]:
        """
        Returns the status of active syscalls.
        """
        return self.syscall_executor.get_active_syscalls()


# Example usage of the SysCallWrapper class
if __name__ == "__main__":
    # Initialize the SysCallWrapper
    syscall_wrapper = SysCallWrapper()

    # Example query for LLM
    llm_query = LLMQuery(agent_name="example_agent", action_type="chat", query="Hello, world!")
    result = syscall_wrapper.send_request("example_agent", llm_query)
    print("LLM Result:", result)

    # Example query for Tool
    tool_query = ToolQuery(agent_name="example_agent", tool_calls=["tool_1", "tool_2"])
    result = syscall_wrapper.send_request("example_agent", tool_query)
    print("Tool Result:", result)

    # Example query for Memory
    mem_query = MemoryQuery(agent_name="example_agent", action_type="retrieve", memory_id=12345)
    result = syscall_wrapper.send_request("example_agent", mem_query)
    print("Memory Result:", result)

    # Example query for Storage
    storage_query = StorageQuery(agent_name="example_agent", action_type="read", file_path="path/to/file")
    result = syscall_wrapper.send_request("example_agent", storage_query)
    print("Storage Result:", result)

    # Retrieve the status of active syscalls
    active_status = syscall_wrapper.get_status()
    print("Active Syscalls Status:", active_status)
