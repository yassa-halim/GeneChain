import json
import logging
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from services.langgraph_service.schemas import SearchQuery
from typing import List, Dict, Union, Generator, Any
from utils.helper_functions import get_custom_logger

log = get_custom_logger(name=__name__)

# Constants for supported roles
ROLES = {
    "assistant": AIMessage,
    "user": HumanMessage,
    "tool": ToolMessage,
}


def log_event(event_name: str, message: str) -> None:
    """
    A utility function to log events with contextual information.
    Args:
        event_name (str): The name of the event.
        message (str): The message to log.
    """
    log.info(f"{event_name}: {message}")


def get_system_message(message: str) -> SystemMessage:
    """
    Create a SystemMessage object from a string message.
    Args:
        message (str): The content of the system message.
    Returns:
        SystemMessage: The SystemMessage object.
    """
    log_event("get_system_message", f"Creating system message with content: {message}")
    return SystemMessage(content=message)


def get_human_message(message: str) -> HumanMessage:
    """
    Create a HumanMessage object from a string message.
    Args:
        message (str): The content of the human message.
    Returns:
        HumanMessage: The HumanMessage object.
    """
    log_event("get_human_message", f"Creating human message with content: {message}")
    return HumanMessage(content=message)


def get_graph_configuration(thread_id: str = "1") -> Dict[str, Dict[str, str]]:
    """
    Returns the configuration for the graph.
    Args:
        thread_id (str): Thread identifier for the current state.
    Returns:
        dict: The configuration dictionary.
    """
    config = {"configurable": {"thread_id": thread_id}}
    log_event("get_graph_configuration", f"Returning configuration: {config}")
    return config


def convert_messages_to_dicts(messages: List[Union[ToolMessage, AIMessage, HumanMessage]]) -> List[Dict[str, Any]]:
    """
    Converts a list of LangChain messages to a list of dictionaries with 'role' and 'content'.
    Args:
        messages (List[Union[ToolMessage, AIMessage, HumanMessage]]): List of LangChain messages.
    Returns:
        List[Dict[str, Any]]: List of dictionaries with 'role' and 'content'.
    """
    converted_messages = []
    for message in messages:
        if isinstance(message, ToolMessage):
            log_event("convert_messages_to_dicts", "Skipping ToolMessage, no conversion implemented.")
            continue  # Skipping ToolMessage as it's not required in the conversion for now
        elif isinstance(message, AIMessage):
            converted_messages.append({"role": "assistant", "content": message.content, "id": message.id})
        elif isinstance(message, HumanMessage):
            converted_messages.append({"role": "user", "content": message.content, "id": message.id})
        else:
            raise ValueError(f"Unsupported message type: {type(message)}")

    log_event("convert_messages_to_dicts", f"Converted messages: {converted_messages}")
    return converted_messages


def convert_dicts_to_messages(dicts: List[Dict[str, Any]]) -> List[Union[ToolMessage, AIMessage, HumanMessage]]:
    """
    Converts a list of dictionaries with 'role' and 'content' to LangChain message objects.
    Args:
        dicts (List[Dict[str, Any]]): List of dictionaries with 'role' and 'content'.
    Returns:
        List[Union[ToolMessage, AIMessage, HumanMessage]]: List of LangChain messages.
    """
    messages = []
    for item in dicts:
        role = item.get("role")
        content = item.get("content")

        message_class = ROLES.get(role)

        if message_class:
            messages.append(message_class(content=content))
        else:
            log_event("convert_dicts_to_messages", f"Skipping unknown role: {role} for item: {item}")

    log_event("convert_dicts_to_messages", f"Converted messages: {messages}")
    return messages



async def streaming_wrapper(agent, messages: List[Dict[str, Any]], graph_config: Dict[str, Dict[str, str]]) :
    """
    Handles streaming results from the LangChain agent and triggers actions based on events.
    Args:
        agent: The LangChain agent.
        messages (List[Dict[str, Any]]): The messages to be passed to the agent.
        graph_config (Dict[str, Dict[str, str]]): The configuration for the graph.
    Yields:
        AsyncGenerator: Yields processed results or error messages.
    """
    try:
        log_event("streaming_wrapper", f"Starting streaming with messages: {messages}")
        agent.search_graph.update_state(graph_config, {"search_query": SearchQuery(), "search_result": {}})
        
        async for event in agent.search_graph.astream_events({"messages": messages}, version="v2", config=graph_config):
            if event["event"] == "on_chain_stream":
                log_event("streaming_wrapper", f"Processing on_chain_stream event: {event}")
                
                if 'messages' in event['data']['chunk']:
                    try:
                        if not isinstance(event["data"]["chunk"]["messages"], list):
                            yield event["data"]["chunk"]["messages"].content
                    except Exception as e:
                        log.error(f"Error processing message content: {e}")
                        yield f"Error: {str(e)}"

            elif event["event"] == "on_chain_end":
                log_event("streaming_wrapper", "Chain has ended.")
                if event["data"] and "output" in event["data"] and "search_result" in event["data"]["output"]:
                    if event["data"]["output"]["search_result"]:
                        result = event["data"]["output"]["search_result"]
                        yield json.dumps(result)
                        return
                else:
                    log_event("streaming_wrapper", "No search result found in output.")
                    yield "No search result found."

            else:
                log_event("streaming_wrapper", f"Unhandled event: {event['event']}")
                yield ""

    except Exception as e:
        log.error(f"Error in streaming_wrapper: {e}")
        yield f"Error: {str(e)}"


def setup_agent(agent, graph_config: Dict[str, Dict[str, str]]) -> None:
    """
    Sets up the LangChain agent with the given graph configuration.
    Args:
        agent: The LangChain agent.
        graph_config (Dict[str, Dict[str, str]]): The configuration for the agent.
    """
    try:
        log_event("setup_agent", f"Setting up agent with graph configuration: {graph_config}")
        agent.search_graph.update_state(graph_config, {"search_query": SearchQuery(), "search_result": {}})
    except Exception as e:
        log.error(f"Error setting up agent: {e}")


def validate_messages(messages: List[Dict[str, Any]]) -> None:
    """
    Validates that the messages list contains necessary keys and valid roles.
    Args:
        messages (List[Dict[str, Any]]): The list of messages to validate.
    Raises:
        ValueError: If the message does not contain the necessary keys or invalid roles.
    """
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("Message must be a dictionary.")
        if "role" not in message or "content" not in message:
            raise ValueError("Message must contain 'role' and 'content' keys.")
        if message["role"] not in ROLES:
            raise ValueError(f"Invalid role: {message['role']}. Supported roles: {', '.join(ROLES.keys())}.")

    log_event("validate_messages", f"Messages validated successfully: {messages}")


# Example usage: running the entire pipeline with an agent and messages
if __name__ == "__main__":
    try:
        # Initialize agent and graph configuration
        agent = None  # Assuming agent is already initialized elsewhere
        graph_config = get_graph_configuration("1")
        
        # Example message stream
        messages = [{"role": "user", "content": "What is LangChain?"}]
        
        # Setup agent with the graph configuration
        setup_agent(agent, graph_config)

        # Validate messages before processing
        validate_messages(messages)

        # Start the streaming wrapper
        result = streaming_wrapper(agent, messages, graph_config)
        for chunk in result:
            log_event("main", f"Received stream chunk: {chunk}")
    
    except Exception as e:
        log.error(f"Error in main execution: {e}")
