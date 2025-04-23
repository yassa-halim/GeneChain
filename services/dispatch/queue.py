from threading import Thread
from queue import Queue, Empty
import heapq
import time
import traceback
import MemoryRequest, BaseMemoryManager, Memory
import SchedulerLogger
import LLMRequestQueueGetMessage
import MemoryRequestQueueGetMessage
import ToolRequestQueueGetMessage
import StorageRequestQueueGetMessage
import MemoryManager
import StorageManager
import LLMAdapter
import ToolManager
import ZLIBCompressor

class UniformedMemoryManager(BaseMemoryManager):
    def __init__(self, max_memory_block_size, memory_block_num):
        super().__init__(max_memory_block_size, memory_block_num)
        self.memory_blocks = [Memory(max_memory_block_size) for _ in range(memory_block_num)]
        self.free_memory_blocks = [i for i in range(0, memory_block_num)]
        self.thread = Thread(target=self.run)

        self.aid_to_memory = dict() 
        self.compressor = ZLIBCompressor() 
        heapq.heapify(self.free_memory_blocks)
        self.memory_operation_queue = Queue()

    def start(self):
        self.active = True
        self.thread.start()

    def stop(self):
        self.active = False
        self.thread.join()

    def run(self):
        while self.active:
            try:
                memory_request = self.memory_operation_queue.get(block=True, timeout=0.1)
                self.execute_operation(memory_request)
            except Empty:
                pass

    def execute_operation(self, memory_request: MemoryRequest):
        operation_type = memory_request.operation_type
        if operation_type == "write":
            self.mem_write(agent_id=memory_request.agent_id, content=memory_request.content)
        elif operation_type == "read":
            self.mem_read(agent_id=memory_request.agent_id, round_id=memory_request.round_id)

    def mem_write(self, agent_id, round_id: str, content: str):
        compressed_content = self.compressor.compress(content)
        size = len(compressed_content)
        memory_block_id = self.aid_to_memory[agent_id][round_id]["memory_block_id"]
        address = self.memory_blocks[memory_block_id].mem_alloc(size)
        self.memory_blocks[memory_block_id].mem_write(address, compressed_content)

    def mem_read(self, agent_id, round_id):
        memory_block_id = self.aid_to_memory[agent_id][round_id]["memory_block_id"]
        data = self.memory_blocks[memory_block_id].mem_read(
            self.aid_to_memory[agent_id][round_id]["address"],
            self.aid_to_memory[agent_id][round_id]["size"]
        )
        return data

    def mem_alloc(self, agent_id):
        memory_block_id = heapq.heappop(self.free_memory_blocks)
        self.aid_to_memory[agent_id] = {"memory_block_id": memory_block_id}

    def mem_clear(self, agent_id):
        memory_block = self.aid_to_memory.pop(agent_id)
        memory_block_id = memory_block['memory_block_id']
        heapq.heappush(self.free_memory_blocks, memory_block_id)

class Scheduler:
    def __init__(self, llm: LLMAdapter, memory_manager: MemoryManager, storage_manager: StorageManager, tool_manager: ToolManager, log_mode, get_llm_syscall: LLMRequestQueueGetMessage, get_memory_syscall: MemoryRequestQueueGetMessage, get_storage_syscall: StorageRequestQueueGetMessage, get_tool_syscall: ToolRequestQueueGetMessage):
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

    def start(self):
        self.active = True
        for name, thread_value in self.request_processors.items():
            thread_value.start()

    def stop(self):
        self.active = False
        for name, thread_value in self.request_processors.items():
            thread_value.join()

    def setup_logger(self):
        logger = SchedulerLogger("Scheduler", self.log_mode)
        return logger

    def run_llm_syscall(self):
        while self.active:
            try:
                llm_syscall = self.get_llm_syscall()
                llm_syscall.set_status("executing")
                self.logger.log(f"{llm_syscall.agent_name} is executing.", "execute")
                llm_syscall.set_start_time(time.time())
                response = self.llm.address_syscall(llm_syscall)
                llm_syscall.set_response(response)
                llm_syscall.event.set()
                llm_syscall.set_status("done")
                llm_syscall.set_end_time(time.time())
            except Empty:
                pass
            except Exception:
                traceback.print_exc()

    def run_memory_syscall(self):
        while self.active:
            try:
                memory_syscall = self.get_memory_syscall()
                memory_syscall.set_status("executing")
                self.logger.log(f"{memory_syscall.agent_name} is executing.", "execute")
                memory_syscall.set_start_time(time.time())
                response = self.memory_manager.address_request(memory_syscall)
                memory_syscall.set_response(response)
                memory_syscall.event.set()
                memory_syscall.set_status("done")
                memory_syscall.set_end_time(time.time())
            except Empty:
                pass
            except Exception:
                traceback.print_exc()

    def run_storage_syscall(self):
        while self.active:
            try:
                storage_syscall = self.get_storage_syscall()
                storage_syscall.set_status("executing")
                self.logger.log(f"{storage_syscall.agent_name} is executing.", "execute")
                storage_syscall.set_start_time(time.time())
                response = self.storage_manager.address_request(storage_syscall)
                storage_syscall.set_response(response)
                storage_syscall.event.set()
                storage_syscall.set_status("done")
                storage_syscall.set_end_time(time.time())
                self.logger.log(f"Current request of {storage_syscall.agent_name} is done.", "done")
            except Empty:
                pass
            except Exception:
                traceback.print_exc()

    def run_tool_syscall(self):
        while self.active:
            try:
                tool_syscall = self.get_tool_syscall()
                tool_syscall.set_status("executing")
                tool_syscall.set_start_time(time.time())
                response = self.tool_manager.address_request(tool_syscall)
                tool_syscall.set_response(response)
                tool_syscall.event.set()
                tool_syscall.set_status("done")
                tool_syscall.set_end_time(time.time())
            except Empty:
                pass
            except Exception:
                traceback.print_exc()

class FIFOScheduler(Scheduler):
    def __init__(self, llm: LLMAdapter, memory_manager: MemoryManager, storage_manager: StorageManager, tool_manager: ToolManager, log_mode, get_llm_syscall: LLMRequestQueueGetMessage, get_memory_syscall: MemoryRequestQueueGetMessage, get_storage_syscall: StorageRequestQueueGetMessage, get_tool_syscall: ToolRequestQueueGetMessage):
        super().__init__(llm, memory_manager, storage_manager, tool_manager, log_mode, get_llm_syscall, get_memory_syscall, get_storage_syscall, get_tool_syscall)

    def run_llm_syscall(self):
        while self.active:
            try:
                llm_syscall = self.get_llm_syscall()
                llm_syscall.set_status("executing")
                self.logger.log(f"{llm_syscall.agent_name} is executing.", "execute")
                llm_syscall.set_start_time(time.time())
                response = self.llm.address_syscall(llm_syscall)
                llm_syscall.set_response(response)
                llm_syscall.event.set()
                llm_syscall.set_status("done")
                llm_syscall.set_end_time(time.time())
            except Empty:
                pass
            except Exception:
                traceback.print_exc()

    def run_memory_syscall(self):
        while self.active:
            try:
                memory_syscall = self.get_memory_syscall()
                memory_syscall.set_status("executing")
                self.logger.log(f"{memory_syscall.agent_name} is executing.", "execute")
                memory_syscall.set_start_time(time.time())
                response = self.memory_manager.address_request(memory_syscall)
                memory_syscall.set_response(response)
                memory_syscall.event.set()
                memory_syscall.set_status("done")
                memory_syscall.set_end_time(time.time())
            except Empty:
                pass
            except Exception:
                traceback.print_exc()

    def run_storage_syscall(self):
        while self.active:
            try:
                storage_syscall = self.get_storage_syscall()
                storage_syscall.set_status("executing")
                self.logger.log(f"{storage_syscall.agent_name} is executing.", "execute")
                storage_syscall.set_start_time(time.time())
                response = self.storage_manager.address_request(storage_syscall)
                storage_syscall.set_response(response)
                storage_syscall.event.set()
                storage_syscall.set_status("done")
                storage_syscall.set_end_time(time.time())
                self.logger.log(f"Current request of {storage_syscall.agent_name} is done.", "done")
            except Empty:
                pass
            except Exception:
                traceback.print_exc()

    def run_tool_syscall(self):
        while self.active:
            try:
                tool_syscall = self.get_tool_syscall()
                tool_syscall.set_status("executing")
                tool_syscall.set_start_time(time.time())
                response = self.tool_manager.address_request(tool_syscall)
                tool_syscall.set_response(response)
                tool_syscall.event.set()
                tool_syscall.set_status("done")
                tool_syscall.set_end_time(time.time())
            except Empty:
                pass
            except Exception:
                traceback.print_exc()
