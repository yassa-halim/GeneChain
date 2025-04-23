import random
import uuid
import time
import logging
from typing import Optional, Union

# Setup logging for better traceability
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants for the ID generation ranges
DEFAULT_MIN_ID = 0
DEFAULT_MAX_ID = 1000
UUID_NAMESPACE = uuid.NAMESPACE_DNS

# Error handling for invalid input
class ToolCallIDError(Exception):
    """Custom exception for invalid tool call ID operations."""
    pass


class GeneratorToolCallID:
    """
    Class to generate tool call IDs. Supports various strategies for generating IDs, such as:
    - Random integer within a specified range
    - UUID-based generation for globally unique IDs
    """
    
    def __init__(self, min_id: int = DEFAULT_MIN_ID, max_id: int = DEFAULT_MAX_ID, use_uuid: bool = False):
        """
        Initializes the ID generator.
        
        :param min_id: Minimum range for random ID generation.
        :param max_id: Maximum range for random ID generation.
        :param use_uuid: Whether to use UUID for tool call ID generation.
        """
        self.min_id = min_id
        self.max_id = max_id
        self.use_uuid = use_uuid
        logger.debug(f"Initialized GeneratorToolCallID with range ({self.min_id}, {self.max_id}) and UUID set to {self.use_uuid}")

    def generate_random_id(self) -> str:
        """
        Generates a random integer-based ID within a specified range.
        
        :return: A string representation of the generated ID.
        """
        random_id = random.randint(self.min_id, self.max_id)
        logger.debug(f"Generated random ID: {random_id}")
        return str(random_id)

    def generate_uuid(self) -> str:
        """
        Generates a UUID based tool call ID.
        
        :return: A string representation of the UUID.
        """
        generated_uuid = str(uuid.uuid5(UUID_NAMESPACE, str(time.time())))
        logger.debug(f"Generated UUID ID: {generated_uuid}")
        return generated_uuid

    def generate_tool_call_id(self) -> str:
        """
        Generates the tool call ID using the selected strategy.
        
        :return: A string representation of the generated ID.
        """
        if self.use_uuid:
            return self.generate_uuid()
        else:
            return self.generate_random_id()


class ToolCallIDValidator:
    """
    A utility class to validate the generated tool call IDs.
    """

    @staticmethod
    def is_valid_random_id(tool_call_id: str, min_id: int = DEFAULT_MIN_ID, max_id: int = DEFAULT_MAX_ID) -> bool:
        """
        Validates if the given ID is within the valid random ID range.
        
        :param tool_call_id: The tool call ID to validate.
        :param min_id: The minimum valid ID value.
        :param max_id: The maximum valid ID value.
        :return: Boolean indicating if the ID is valid.
        """
        try:
            id_int = int(tool_call_id)
            is_valid = min_id <= id_int <= max_id
            if not is_valid:
                logger.error(f"Invalid random ID: {tool_call_id}. Must be between {min_id} and {max_id}.")
            return is_valid
        except ValueError:
            logger.error(f"Tool call ID {tool_call_id} is not a valid integer.")
            return False

    @staticmethod
    def is_valid_uuid(tool_call_id: str) -> bool:
        """
        Validates if the given ID is a valid UUID.
        
        :param tool_call_id: The tool call ID to validate.
        :return: Boolean indicating if the ID is a valid UUID.
        """
        try:
            uuid_obj = uuid.UUID(tool_call_id, version=5)
            return str(uuid_obj) == tool_call_id
        except ValueError:
            logger.error(f"Tool call ID {tool_call_id} is not a valid UUID.")
            return False


class ToolCallIDManager:
    """
    A manager class that handles the generation, validation, and logging of tool call IDs.
    """

    def __init__(self, min_id: int = DEFAULT_MIN_ID, max_id: int = DEFAULT_MAX_ID, use_uuid: bool = False):
        """
        Initializes the manager with specified parameters.
        
        :param min_id: Minimum range for random ID generation.
        :param max_id: Maximum range for random ID generation.
        :param use_uuid: Whether to use UUID for tool call ID generation.
        """
        self.generator = GeneratorToolCallID(min_id, max_id, use_uuid)
        self.validator = ToolCallIDValidator()
        logger.debug("ToolCallIDManager initialized.")

    def generate_and_validate_id(self) -> Union[str, None]:
        """
        Generates a new tool call ID and validates it.
        
        :return: A valid tool call ID or None if validation fails.
        """
        tool_call_id = self.generator.generate_tool_call_id()
        logger.debug(f"Generated tool call ID: {tool_call_id}")

        if self.validator.is_valid_random_id(tool_call_id):
            logger.info(f"Valid random tool call ID: {tool_call_id}")
            return tool_call_id
        elif self.validator.is_valid_uuid(tool_call_id):
            logger.info(f"Valid UUID tool call ID: {tool_call_id}")
            return tool_call_id
        else:
            logger.error(f"Invalid tool call ID generated: {tool_call_id}.")
            return None


class ToolCallIDTracker:
    """
    A utility class to track tool call IDs with timestamp.
    """

    def __init__(self):
        """
        Initializes the tracker.
        """
        self.tool_call_log = []
        logger.debug("ToolCallIDTracker initialized.")

    def track_tool_call(self, tool_call_id: str):
   
        timestamp = time.time()
        self.tool_call_log.append((tool_call_id, timestamp))
        logger.info(f"Tracked tool call ID: {tool_call_id} at {timestamp}")

    def get_tool_call_log(self):
        """
        Retrieves the logged tool call IDs.
        
        :return: A list of tool call IDs with timestamps.
        """
        return self.tool_call_log


# Extended functionalities: Random ID Generation with user-defined input
class AdvancedGeneratorToolCallID(GeneratorToolCallID):
    """
    A more advanced version of the GeneratorToolCallID class, allowing more control over ID generation.
    """

    def __init__(self, min_id: int = DEFAULT_MIN_ID, max_id: int = DEFAULT_MAX_ID, use_uuid: bool = False, allow_retries: bool = False):
        """
        Initializes the advanced generator with more options like retries.
        
        :param min_id: Minimum range for random ID generation.
        :param max_id: Maximum range for random ID generation.
        :param use_uuid: Whether to use UUID for tool call ID generation.
        :param allow_retries: Whether to allow retries on failed ID generation.
        """
        super().__init__(min_id, max_id, use_uuid)
        self.allow_retries = allow_retries
        logger.debug("AdvancedGeneratorToolCallID initialized.")

    def generate_tool_call_id_with_retry(self, max_retries: int = 3) -> str:
        """
        Tries to generate a tool call ID with a set number of retries in case of failure.
        
        :param max_retries: Maximum number of retries allowed.
        :return: A valid tool call ID after retries.
        """
        retries = 0
        while retries < max_retries:
            tool_call_id = self.generate_tool_call_id()
            if self.is_valid_tool_call_id(tool_call_id):
                logger.info(f"Generated valid tool call ID: {tool_call_id} after {retries} retries.")
                return tool_call_id
            retries += 1
            logger.warning(f"Retrying ID generation, attempt {retries}/{max_retries}.")
        raise ToolCallIDError(f"Failed to generate a valid tool call ID after {max_retries} retries.")

    def is_valid_tool_call_id(self, tool_call_id: str) -> bool:
        """
        Validates the generated tool call ID.
        
        :param tool_call_id: Tool call ID to validate.
        :return: Boolean indicating whether the ID is valid.
        """
        return self.is_valid_random_id(tool_call_id) or self.is_valid_uuid(tool_call_id)


# Example usage
def main():
    logger.info("Tool Call ID Generation and Validation")
    
    # Initialize the manager and generator
    tool_call_manager = ToolCallIDManager()
    
    # Generate and validate a new tool call ID
    tool_call_id = tool_call_manager.generate_and_validate_id()
    if tool_call_id:
        logger.info(f"Generated valid tool call ID: {tool_call_id}")
    else:
        logger.error("Failed to generate a valid tool call ID.")

    # Advanced generation with retries
    advanced_generator = AdvancedGeneratorToolCallID()
    try:
        tool_call_id_with_retry = advanced_generator.generate_tool_call_id_with_retry()
        logger.info(f"Generated tool call ID with retry: {tool_call_id_with_retry}")
    except ToolCallIDError as e:
        logger.error(e)

    # Track tool call ID
    tracker = ToolCallIDTracker()
    tracker.track_tool_call(tool_call_id_with_retry)
    log = tracker.get_tool_call_log()
    logger.info(f"Logged tool call IDs: {log}")