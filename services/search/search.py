import time
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any

from services.external_services.oxylabs import get_oxylabs_search_result
from services.langgraph_service.agent import LangGraphAgent
from services.langgraph_service.utils import (
    get_human_message,
    get_graph_configuration,
    streaming_wrapper
)
from utils.helper_functions import get_custom_logger
from config import OXYLABS_PRICING_SOURCE


# Initialize logger
log = get_custom_logger(name=__name__)

# FastAPI router initialization
router = APIRouter(tags=["Search"], prefix="/search")

# Initialize agent
agent = LangGraphAgent(model_name="groq")


# Utility functions

def log_request_start(endpoint: str, params: Dict[str, Any]) -> None:
    """
    Utility function to log the start of an API request.
    Args:
        endpoint (str): The API endpoint being called.
        params (dict): The parameters being passed to the endpoint.
    """
    log.info(f"Request to {endpoint} started with parameters: {params}")


def log_request_end(endpoint: str, elapsed_time: float) -> None:
    """
    Utility function to log the end of an API request.
    Args:
        endpoint (str): The API endpoint being called.
        elapsed_time (float): The time taken to process the request.
    """
    log.info(f"Request to {endpoint} completed in {elapsed_time:.2f} seconds.")


# API Endpoints

@router.post("/generate_search_query")
async def generate_search_query(user_query: str, chat_id: str, max_tokens: Optional[int] = Query(150, alias="max_tokens")):
    """
    Endpoint to generate search query using LangGraph agent.
    Args:
        user_query (str): The query from the user.
        chat_id (str): Unique identifier for the conversation.
        max_tokens (int): Optional parameter to limit the number of tokens for the response.
    Returns:
        StreamingResponse: Streams the response from the LangGraph agent.
    """
    log_request_start("/generate_search_query", {"user_query": user_query, "chat_id": chat_id, "max_tokens": max_tokens})

    try:
        human_message = get_human_message(message=user_query)
        messages = [human_message]

        graph_config = get_graph_configuration(thread_id=chat_id)

        # Start streaming the response from the LangGraph agent
        start_time = time.time()
        log.info("Calling search agent to generate search query.")
        response = StreamingResponse(
            streaming_wrapper(agent=agent, messages=messages, graph_config=graph_config),
            media_type="application/json"
        )
        log_request_end("/generate_search_query", time.time() - start_time)
        return response
    except Exception as e:
        log.error(f"Error generating search query for chat_id={chat_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while generating the search query: {str(e)}")


@router.get("/visualize")
async def visualize():
    """
    Endpoint to visualize the search graph.
    Returns:
        str: Returns the visualization of the search graph.
    """
    log_request_start("/visualize", {})
    try:
        visualization = agent.visualize()
        log_request_end("/visualize", 0)  # Assume the visualization process is fast
        return visualization
    except Exception as e:
        log.error(f"Error visualizing search graph: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while visualizing the search graph: {str(e)}")


@router.post("/product_pricing", response_model=dict)
async def product_pricing(product_id: str, region: Optional[str] = "US"):
    """
    Endpoint to get product pricing from Oxylabs.
    Args:
        product_id (str): The ID of the product to query.
        region (str): Optional region for the pricing query.
    Returns:
        dict: The product pricing details.
    """
    log_request_start("/product_pricing", {"product_id": product_id, "region": region})
    start_time = time.time()

    try:
        # Fetching pricing details using Oxylabs service
        data = get_oxylabs_search_result(
            search_engine=OXYLABS_PRICING_SOURCE,
            user_query=product_id,
            region=region
        )

        log_request_end("/product_pricing", time.time() - start_time)
        return {"pricing_result": data}
    except Exception as e:
        log.error(f"Error getting product pricing for product_id={product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching product pricing: {str(e)}")


# Enhanced Search Query Handler

def get_enriched_search_query(user_query: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    Enriches the search query with additional context or metadata.
    Args:
        user_query (str): The original user query.
        context (str): Optional additional context for the query.
    Returns:
        dict: The enriched query with context and metadata.
    """
    enriched_query = {
        "user_query": user_query,
        "metadata": {
            "context": context if context else "general",
            "timestamp": time.time(),
            "source": "LangGraphAgent",
        }
    }
    log("get_enriched_search_query", f"Enriched query: {enriched_query}")
    return enriched_query


# Enhanced Error Handling and Retry Logic

async def retry_on_failure(func, retries: int = 3, delay: int = 2, *args, **kwargs):
    """
    A helper function to retry API calls on failure.
    Args:
        func (callable): The function to retry.
        retries (int): Number of retry attempts.
        delay (int): Delay between retries in seconds.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.
    Returns:
        The result of the function call.
    """
    last_exception = None
    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            log.error(f"Attempt {attempt + 1} failed: {str(e)}")
        
    raise last_exception


# Extended Streaming Wrapper

async def extended_streaming_wrapper(agent: LangGraphAgent, messages: list, graph_config: dict):
    """
    Extended version of streaming wrapper with advanced handling.
    Args:
        agent (LangGraphAgent): The agent to handle the search process.
        messages (list): The user messages.
        graph_config (dict): Configuration for the search graph.
    Returns:
        StreamingResponse: The streaming response.
    """
    try:
        log("extended_streaming_wrapper", "Starting streaming.")
        async for event in agent.search_graph.astream_events({"messages": messages}, version="v2", config=graph_config):
            if event["event"] == "on_chain_stream":
                log("extended_streaming_wrapper", f"Received streaming data: {event}")
                yield event["data"]["chunk"]
            elif event["event"] == "on_chain_end":
                log("extended_streaming_wrapper", "Chain has ended, sending final results.")
            else:
                log("extended_streaming_wrapper", f"Unhandled event type: {event['event']}")
    except Exception as e:
        log.error(f"Error in extended streaming: {str(e)}")
        yield f"Error: {str(e)}"
