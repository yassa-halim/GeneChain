import MemoryManager
import StorageManager
import LLMAdapter
import ToolManager
import LLMRequestQueueGetMessage
import MemoryRequestQueueGetMessage
import ToolRequestQueueGetMessage
import StorageRequestQueueGetMessage
import SchedulerLogger
from threading import Thread
from queue import Queue, Empty
from time import sleep

class Scheduler:
    def __init__(
        self,
        llm: LLMAdapter,
        memory_manager: MemoryManager,
        storage_manager: StorageManager,
        tool_manager: ToolManager,
        log_mode,
        get_llm_syscall: LLMRequestQueueGetMessage,
        get_memory_syscall: MemoryRequestQueueGetMessage,
        get_storage_syscall: StorageRequestQueueGetMessage,
        get_tool_syscall: ToolRequestQueueGetMessage,
    ):
        self.get_llm_syscall = get_llm_syscall
        self.get_memory_syscall = get_memory_syscall
        self.get_storage_syscall = get_storage_syscall
        self.get_tool_syscall = get_tool_syscall
        self.active = False
        self.log_mode = log_mode
        self.logger = self.setup_logger()
        self.request_processors = {
            "llm_syscall_processor": Thread(target=self.run_llm_syscall),
            "mem_syscall_processor": Thread(target=self.run_memory_syscall),
            "sto_syscall_processor": Thread(target=self.run_storage_syscall),
            "tool_syscall_processor": Thread(target=self.run_tool_syscall),
        }
        self.llm = llm
        self.memory_manager = memory_manager
        self.storage_manager = storage_manager
        self.tool_manager = tool_manager

        self.llm_queue = Queue()
        self.memory_queue = Queue()
        self.storage_queue = Queue()
        self.tool_queue = Queue()

    def start(self):
        """ Start the scheduler """
        self.active = True
        for name, thread_value in self.request_processors.items():
            thread_value.start()

    def stop(self):
        """ Stop the scheduler """
        self.active = False
        for name, thread_value in self.request_processors.items():
            thread_value.join()

    def setup_logger(self):
        logger = SchedulerLogger("Scheduler", self.log_mode)
        return logger

    def run_llm_syscall(self):
        """Process LLM system calls"""
        while self.active:
            try:
                message = self.get_llm_syscall()
                self.process_llm_request(message)
            except Empty:
                sleep(0.1)  # Sleep to reduce busy-waiting

    def run_memory_syscall(self):
        """Process Memory system calls"""
        while self.active:
            try:
                message = self.get_memory_syscall()
                self.process_memory_request(message)
            except Empty:
                sleep(0.1)

    def run_storage_syscall(self):
        """Process Storage system calls"""
        while self.active:
            try:
                message = self.get_storage_syscall()
                self.process_storage_request(message)
            except Empty:
                sleep(0.1)

    def run_tool_syscall(self):
        """Process Tool system calls"""
        while self.active:
            try:
                message = self.get_tool_syscall()
                self.process_tool_request(message)
            except Empty:
                sleep(0.1)

    def process_llm_request(self, message):
        """Process an LLM request"""
        try:
            self.logger.log("Processing LLM request...")
            response = self.llm.process_request(message)
            self.llm_queue.put(response)
            self.logger.log(f"LLM Response: {response}")
        except Exception as e:
            self.logger.log(f"Error processing LLM request: {str(e)}")

    def process_memory_request(self, message):
        """Process a memory request"""
        try:
            self.logger.log("Processing Memory request...")
            response = self.memory_manager.process_request(message)
            self.memory_queue.put(response)
            self.logger.log(f"Memory Response: {response}")
        except Exception as e:
            self.logger.log(f"Error processing Memory request: {str(e)}")

    def process_storage_request(self, message):
        """Process a storage request"""
        try:
            self.logger.log("Processing Storage request...")
            response = self.storage_manager.process_request(message)
            self.storage_queue.put(response)
            self.logger.log(f"Storage Response: {response}")
        except Exception as e:
            self.logger.log(f"Error processing Storage request: {str(e)}")

    def process_tool_request(self, message):
        """Process a tool request"""
        try:
            self.logger.log("Processing Tool request...")
            response = self.tool_manager.process_request(message)
            self.tool_queue.put(response)
            self.logger.log(f"Tool Response: {response}")
        except Exception as e:
            self.logger.log(f"Error processing Tool request: {str(e)}")
