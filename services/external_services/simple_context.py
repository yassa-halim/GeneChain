import os
import logging
import torch
from typing import Any
import BaseContextManager
from time import time
from collections import deque

# Constants for file storage, cache limits, and error handling.
MAX_CONTEXT_CACHE_SIZE = 50  # Max cache size before purging old contexts
MAX_RETRY_ATTEMPTS = 5
RETRY_DELAY = 2  # seconds
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOGGING_FILE = "context_manager.log"

# Setup logging
logging.basicConfig(format=LOGGING_FORMAT, level=logging.INFO, filename=LOGGING_FILE)
log = logging.getLogger(__name__)

class SimpleContextManager(BaseContextManager):
    def __init__(self):
        super().__init__()
        self.context_dict = {}
        self.context_cache = deque(maxlen=MAX_CONTEXT_CACHE_SIZE)  # A queue to manage cache size
        self.context_dir = "context_snapshots"  # Default directory for storing snapshots
        self._ensure_dir_exists(self.context_dir)
        log.info("SimpleContextManager initialized.")

    def _ensure_dir_exists(self, directory: str):
        """Helper function to ensure the context directory exists."""
        if not os.path.exists(directory):
            log.info(f"Creating directory for context snapshots: {directory}")
            os.makedirs(directory)

    def start(self):
        log.info("Context Manager started.")
        # Additional setup logic if required in the future (like DB connections, etc.)

    def gen_snapshot(self, pid: str, context: Any):
        """
        Generates a snapshot of the context for a given process ID (pid).

        Args:
            pid (str): Process ID for identifying the context.
            context (Any): The context to be saved, usually the model's state or execution context.
        """
        try:
            log.info(f"Generating snapshot for process {pid}.")
            file_path = os.path.join(self.context_dir, f"process-{pid}.pt")
            torch.save(context, file_path)  # Save the context as a .pt file
            self.context_dict[str(pid)] = context  # Keep it in memory as well
            self.context_cache.append((str(pid), context))  # Cache the context for quick access
            log.info(f"Snapshot for process {pid} saved successfully.")
        except Exception as e:
            log.error(f"Error while generating snapshot for process {pid}: {str(e)}")

    def gen_recover(self, pid: str) -> Any:
        """
        Recovers the snapshot for a given process ID (pid).

        Args:
            pid (str): Process ID for identifying the context.

        Returns:
            context: The recovered context (usually the model's state).
        """
        try:
            log.info(f"Attempting to recover snapshot for process {pid}.")
            # First check in memory
            if pid in self.context_dict:
                log.info(f"Recovered context for process {pid} from memory.")
                return self.context_dict[pid]

            # If not in memory, check the snapshot directory
            file_path = os.path.join(self.context_dir, f"process-{pid}.pt")
            if os.path.exists(file_path):
                context = torch.load(file_path)
                log.info(f"Recovered context for process {pid} from disk.")
                self.context_dict[str(pid)] = context  # Cache it in memory
                return context
            else:
                log.warning(f"Snapshot for process {pid} does not exist.")
                return None
        except Exception as e:
            log.error(f"Error while recovering snapshot for process {pid}: {str(e)}")
            return None

    def check_restoration(self, pid: str) -> bool:
        """
        Checks if a snapshot exists for the given process ID (pid).

        Args:
            pid (str): Process ID to check for restoration.
        
        Returns:
            bool: True if the snapshot exists, False otherwise.
        """
        # First check in memory cache
        if pid in self.context_dict:
            return True

        # Then check in the snapshot directory
        file_path = os.path.join(self.context_dir, f"process-{pid}.pt")
        return os.path.exists(file_path)

    def clear_restoration(self, pid: str):
        """
        Clears the snapshot data for a given process ID (pid).

        Args:
            pid (str): Process ID to delete context for.
        """
        try:
            log.info(f"Clearing restoration data for process {pid}.")
            # Remove from in-memory context dictionary
            if pid in self.context_dict:
                del self.context_dict[pid]
                log.info(f"In-memory context for process {pid} cleared.")

            # Remove from snapshot directory
            file_path = os.path.join(self.context_dir, f"process-{pid}.pt")
            if os.path.exists(file_path):
                os.remove(file_path)
                log.info(f"Snapshot for process {pid} deleted from disk.")
            else:
                log.warning(f"Snapshot for process {pid} not found on disk.")
        except Exception as e:
            log.error(f"Error while clearing restoration for process {pid}: {str(e)}")

    def stop(self):
        """
        Stops the context manager and cleans up resources if necessary.
        """
        log.info("Context Manager stopped.")
        # Additional cleanup code (e.g., closing DB connections, etc.)

    def _retry_on_failure(self, function, *args, retries=MAX_RETRY_ATTEMPTS, delay=RETRY_DELAY, **kwargs):
        """
        Helper function to retry a given function in case of failure.

        Args:
            function (callable): The function to execute.
            *args: Arguments for the function.
            **kwargs: Keyword arguments for the function.
            retries (int): The number of retry attempts.
            delay (int): The delay between retries in seconds.
        
        Returns:
            Any: The result of the function if successful, raises exception after retries.
        """
        for attempt in range(retries):
            try:
                return function(*args, **kwargs)
            except Exception as e:
                log.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < retries - 1:
                    log.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise e

    def restore_from_cache(self, pid: str) -> Any:
        """
        Restores the context for the given PID from the cache if it exists.

        Args:
            pid (str): The process ID for which to restore the context.

        Returns:
            context (Any): The restored context, or None if not found.
        """
        log.info(f"Restoring context for process {pid} from cache.")
        for cached_pid, context in self.context_cache:
            if cached_pid == pid:
                log.info(f"Found cached context for process {pid}.")
                return context
        log.warning(f"No cached context found for process {pid}.")
        return None

    def log_context_details(self, pid: str) -> None:
        """
        Logs detailed information about the context for the given PID.

        Args:
            pid (str): The process ID to log details for.
        """
        log.info(f"Logging context details for process {pid}.")
        if pid in self.context_dict:
            context = self.context_dict[pid]
            log.info(f"Context for process {pid} (memory): {context}")
        else:
            log.warning(f"No context found in memory for process {pid}.")

    def clean_old_snapshots(self) -> None:
        """
        Cleans old snapshots from disk if the cache exceeds the maximum size.
        """
        try:
            if len(self.context_dict) > MAX_CONTEXT_CACHE_SIZE:
                # Purge the oldest context from cache
                oldest_pid, oldest_context = self.context_cache.popleft()
                self.clear_restoration(oldest_pid)
                log.info(f"Purged old context for process {oldest_pid} to maintain cache size.")
        except Exception as e:
            log.error(f"Error while cleaning old snapshots: {str(e)}")

    def monitor_context_usage(self) -> None:
        """
        Monitors and logs the usage of the context storage.
        """
        log.info(f"Monitoring context storage usage. Current in-memory contexts: {len(self.context_dict)}")
        log.info(f"Current cached contexts: {len(self.context_cache)}")
        log.info(f"Total snapshots on disk: {len(os.listdir(self.context_dir))}")

    def get_context_snapshot_info(self, pid: str) -> dict:
        """
        Retrieves detailed information about the snapshot for the given PID.

        Args:
            pid (str): The process ID to retrieve snapshot information for.

        Returns:
            dict: Information about the context snapshot (size, creation date, etc.).
        """
        try:
            file_path = os.path.join(self.context_dir, f"process-{pid}.pt")
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                creation_time = time.ctime(os.path.getctime(file_path))
                return {"file_path": file_path, "size": file_size, "creation_time": creation_time}
            else:
                log.warning(f"No snapshot file found for process {pid}.")
                return {}
        except Exception as e:
            log.error(f"Error while retrieving snapshot info for process {pid}: {str(e)}")
            return {}