import heapq
from queue import Queue, Empty
from threading import Lock, Thread
import MemoryRequest, BaseMemoryManager, Memory
from utils.compressor import ZLIBCompressor

class UniformedMemoryManager(BaseMemoryManager):
    def __init__(self, max_memory_block_size, memory_block_num):
        super().__init__(max_memory_block_size, memory_block_num)
        
        self.memory_blocks = [Memory(max_memory_block_size) for _ in range(memory_block_num)]
        self.free_memory_blocks = [i for i in range(0, memory_block_num)]
        heapq.heapify(self.free_memory_blocks)
        
        self.aid_to_memory = {}  # Map agent_id -> memory_block_id, address, size, etc.
        self.compressor = ZLIBCompressor()  # For compressing data before storing in memory
        self.memory_operation_queue = Queue()
        self.thread = Thread(target=self.run)
        
        self.lock = Lock()  # Lock for memory access to ensure thread-safety
        self.active = False

    def start(self):
        """ Start the memory manager and the operation scheduler thread. """
        self.active = True
        self.thread.start()

    def stop(self):
        """ Stop the memory manager and the operation scheduler thread. """
        self.active = False
        self.thread.join()

    def run(self):
        """ Runs the scheduler that processes memory operations. """
        while self.active:
            try:
                memory_request = self.memory_operation_queue.get(block=True, timeout=0.1)
                self.execute_operation(memory_request)
            except Empty:
                pass

    def execute_operation(self, memory_request: MemoryRequest):
        """ Execute the memory operation based on the type. """
        operation_type = memory_request.operation_type
        if operation_type == "write":
            self.mem_write(agent_id=memory_request.agent_id, content=memory_request.content)
        elif operation_type == "read":
            self.mem_read(agent_id=memory_request.agent_id, round_id=memory_request.round_id)

    def mem_write(self, agent_id, round_id, content):
        """ Write data into memory for a given agent and round. """
        with self.lock:
            compressed_content = self.compressor.compress(content)
            size = len(compressed_content)

            memory_block_id = self.aid_to_memory[agent_id][round_id]["memory_block_id"]
            address = self.memory_blocks[memory_block_id].mem_alloc(size)
            self.memory_blocks[memory_block_id].mem_write(address, compressed_content)

    def mem_read(self, agent_id, round_id):
        """ Read data from memory for a given agent and round. """
        with self.lock:
            memory_block_id = self.aid_to_memory[agent_id][round_id]["memory_block_id"]
            address = self.aid_to_memory[agent_id][round_id]["address"]
            size = self.aid_to_memory[agent_id][round_id]["size"]

            data = self.memory_blocks[memory_block_id].mem_read(address, size)
            return self.compressor.decompress(data)

    def mem_alloc(self, agent_id, size):
        """ Allocate memory block for an agent and return the memory address. """
        with self.lock:
            if not self.free_memory_blocks:
                raise MemoryError("No free memory blocks available.")
            
            memory_block_id = heapq.heappop(self.free_memory_blocks)
            address = self.memory_blocks[memory_block_id].mem_alloc(size)
            
            self.aid_to_memory[agent_id] = {
                "memory_block_id": memory_block_id,
                "address": address,
                "size": size
            }

            return address

    def mem_clear(self, agent_id):
        """ Clear the memory allocated to an agent and return the memory block to the pool. """
        with self.lock:
            if agent_id not in self.aid_to_memory:
                raise ValueError("Agent ID not found in memory allocation.")
            
            memory_block = self.aid_to_memory.pop(agent_id)
            memory_block_id = memory_block['memory_block_id']
            heapq.heappush(self.free_memory_blocks, memory_block_id)

    def queue_memory_request(self, memory_request: MemoryRequest):
        """ Queue memory requests for agents to process in a thread-safe manner. """
        self.memory_operation_queue.put(memory_request)

    def get_memory_status(self):
        """ Get current status of memory blocks, including free and allocated memory. """
        with self.lock:
            status = {
                "free_blocks": self.free_memory_blocks,
                "allocated_blocks": len(self.aid_to_memory),
                "total_blocks": len(self.memory_blocks)
            }
            return status
