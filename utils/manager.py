import importlib
import logging
from typing import Any, Dict
from cerebrum.llm.communication import Response
from cerebrum.interface import AutoTool

# Set up logging for debugging and tracking purposes
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ToolManager:
    """Manages loading and executing tools based on system calls."""
    
    def __init__(self, log_mode: str = "console"):
        """
        Initializes the ToolManager with the given log mode.
        
        Args:
            log_mode (str): Determines where logs should be written ("console" or "file").
        """
        self.log_mode = log_mode
        self.tool_conflict_map = {}
        self.tool_instances_cache = {}

        # Initialize logger with the specified log mode
        self._configure_logger()

    def _configure_logger(self):
        """Configures the logger for console or file logging."""
        if self.log_mode == "file":
            handler = logging.FileHandler('tool_manager.log')
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
        else:
            logger.setLevel(logging.INFO)

    def address_request(self, syscall) -> Response:
        """
        Handles the incoming system call, processes tool calls, and manages conflicts.
        
        Args:
            syscall: The system call containing tool call information.
            
        Returns:
            Response: The result of the tool execution or an error message.
        """
        tool_calls = syscall.tool_calls

        try:
            for tool_call in tool_calls:
                tool_org_and_name, tool_params = (
                    tool_call["name"],
                    tool_call["parameters"]
                )

                if tool_org_and_name in self.tool_conflict_map:
                    logger.warning(f"Tool {tool_org_and_name} is already being processed.")
                    return Response(
                        response_message=f"Tool {tool_org_and_name} is already being processed.",
                        finished=True
                    )

                # Track tool conflict to prevent re-entry during execution
                self.tool_conflict_map[tool_org_and_name] = 1

                # Load the tool and execute it
                tool = self.load_tool_instance(tool_org_and_name)
                if tool is None:
                    return Response(
                        response_message=f"Failed to load tool: {tool_org_and_name}",
                        finished=True
                    )

                # Run the tool and fetch result
                tool_result = tool.run(params=tool_params)

                # Remove from conflict map once the tool has been executed
                self.tool_conflict_map.pop(tool_org_and_name)

                # Log the result of the tool execution
                logger.info(f"Tool {tool_org_and_name} executed successfully. Result: {tool_result}")
                
                return Response(
                    response_message=tool_result,
                    finished=True
                )
                
        except Exception as e:
            logger.error(f"Error in tool execution: {str(e)}")
            return Response(
                response_message=f"Tool calling error: {str(e)}",
                finished=True
            )

    def load_tool_instance(self, tool_org_and_name: str) -> Any:
        """
        Dynamically loads the tool instance from the preloaded tools or creates a new one.
        
        Args:
            tool_org_and_name (str): The identifier for the tool (e.g., "org/tool_name").
            
        Returns:
            Any: The instance of the tool if successful, None if not.
        """
        # Check if the tool is already in cache
        if tool_org_and_name in self.tool_instances_cache:
            logger.info(f"Using cached instance of tool: {tool_org_and_name}")
            return self.tool_instances_cache[tool_org_and_name]

        try:
            # Load the tool class dynamically
            tool_instance = AutoTool.from_preloaded(tool_org_and_name)
            if tool_instance:
                # Cache the instance for future use
                self.tool_instances_cache[tool_org_and_name] = tool_instance
                logger.info(f"Tool {tool_org_and_name} loaded successfully.")
                return tool_instance
            else:
                logger.error(f"Tool {tool_org_and_name} could not be loaded.")
                return None
        except Exception as e:
            logger.error(f"Error loading tool {tool_org_and_name}: {str(e)}")
            return None

    def clear_tool_cache(self):
        """Clears the tool instances cache."""
        logger.info("Clearing tool instance cache.")
        self.tool_instances_cache.clear()

    def list_loaded_tools(self) -> Dict[str, Any]:
        """Returns a list of currently loaded tool instances."""
        return self.tool_instances_cache

    def reload_tool(self, tool_org_and_name: str) -> Any:
        """Reloads a specific tool if necessary."""
        logger.info(f"Reloading tool {tool_org_and_name}.")
        if tool_org_and_name in self.tool_instances_cache:
            del self.tool_instances_cache[tool_org_and_name]
        return self.load_tool_instance(tool_org_and_name)

    def handle_tool_conflicts(self, tool_name: str) -> bool:
        """
        Checks for conflicts in tool calls.
        
        Args:
            tool_name (str): The name of the tool to check.
            
        Returns:
            bool: True if a conflict exists, False otherwise.
        """
        if tool_name in self.tool_conflict_map:
            logger.warning(f"Tool {tool_name} is already in progress.")
            return True
        return False

    def update_tool_configuration(self, config_data: Dict[str, Any]) -> None:
        """
        Updates the tool configurations dynamically based on input data.
        
        Args:
            config_data (dict): The new configuration data for tools.
        """
        # For example, this could involve updating timeouts or dependencies
        logger.info("Updating tool configurations.")
        # Code to update configuration can go here (depends on the structure of config_data)
        pass


class Tool:
    """ A base class representing a generic tool. Subclass this to implement specific tools. """
    def __init__(self, name: str):
        self.name = name

    def run(self, params: Dict[str, Any]) -> str:
        """ Runs the tool with the provided parameters. """
        raise NotImplementedError("Subclasses must implement the `run` method.")


class ExampleTool(Tool):
    """ An example implementation of a tool. """
    def __init__(self, name: str = "example_tool"):
        super().__init__(name)

    def run(self, params: Dict[str, Any]) -> str:
        """ Implements the tool logic. """
        return f"Running {self.name} with parameters: {params}"


def test_tool_manager():
    """ Unit test to verify the functionality of ToolManager. """
    # Create a mock syscall with tool calls
    syscall = type('syscall', (object,), {
        'tool_calls': [
            {'name': 'example_tool', 'parameters': {'param1': 'value1'}}
        ]
    })()

    tool_manager = ToolManager(log_mode="console")

    response = tool_manager.address_request(syscall)
    print(response.response_message)  # Expected output: Running example_tool with parameters: {'param1': 'value1'}

    # Test conflict handling
    tool_manager.address_request(syscall)
    tool_manager.reload_tool('example_tool')


if __name__ == "__main__":
    # Run test function to validate the implementation
    test_tool_manager()
