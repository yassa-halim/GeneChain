import json
import time
import base64
from io import BytesIO
import asyncio
import logging
from langgraph.graph import MessagesState, START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages.tool import ToolMessage
from langgraph.prebuilt import ToolNode
from services.langgraph_service import (
    search_query_generation_prompt,
    ai_assistant_prompt,
    get_llm,
    SearchQuery
)
from services.langgraph_service.utils import get_system_message, get_human_message, async_stream
from services.external_services.serpapi import get_serpapi_search_result
from utils.helper_functions import get_custom_logger

log = get_custom_logger(name=__name__)

# Max retries and delay for better handling of flaky API calls
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # in seconds


class ShoppingAgentState(MessagesState):
    search_query: SearchQuery
    search_result: dict


class LangGraphAgent:
    def __init__(self, model_name: str = "groq"):
        """
        Initialize the LangGraph Agent with LLM model, tools, and search graph.
        """
        start_time = time.time()
        self.llm = get_llm(model=model_name)
        self.search_query_tools = [self.generate_query]
        self.search_graph = self.get_search_agent()
        log.info(f"Agent Initialization took {(time.time() - start_time):.2f} seconds.")

    async def assistant(self, state: ShoppingAgentState):
        """
        Handles interaction between LLM and the shopping agent.
        It processes incoming state and generates a response or triggers a search.
        """
        system_message = get_system_message(message=ai_assistant_prompt)
        log.info("Calling LLM for AI Response or Search Query Generation.")

        assistant_result = self.llm.bind_tools(self.search_query_tools).stream([system_message] + state["messages"])

        async for chunk in async_stream(sync_generator=assistant_result):
            if chunk.additional_kwargs:
                log.info(f"Tool Chunk Type: {type(chunk)}\nChunk: {chunk}\n--------------------------\n")
                yield {"messages": chunk}
                return

            log.info(f"LLM Response Chunk: {chunk.content}")
            yield {"messages": chunk}

    def generate_query(self, user_input: str):
        """
        Generate a search engine friendly query based on user input.
        This transforms the natural language query into something that a search engine can understand.
        """
        log.info(f"Generate Search Query call started with user input: {user_input}.")
        start_time = time.time()
        human_message = get_human_message(message=user_input)
        system_message = get_system_message(message=search_query_generation_prompt)
        structured_llm = self.llm.with_structured_output(SearchQuery)

        try:
            search_query = structured_llm.invoke([system_message, human_message])
            log.info(f"LLM Generated Search Queries: '{search_query.search_queries}' and context {search_query.context} in {(time.time() - start_time):.2f} seconds.")
            return json.dumps({"search_queries": search_query.search_queries, "context": search_query.context})
        except Exception as e:
            log.error(f"Error generating search query: {str(e)}")
            return json.dumps({"search_queries": [], "context": ""})

    async def fetch_google_shopping_results(self, state: ShoppingAgentState):
        """
        Fetch Google shopping results if the query is relevant to a shopping intent.
        This will handle calling external services and retrieving results.
        """
        if isinstance(state["messages"][-1], ToolMessage):
            search_query_result = json.loads(state['messages'][-1].content)
            state["search_query"] = SearchQuery(
                search_queries=search_query_result["search_queries"],
                context=search_query_result["context"]
            )

            log.info(f"Search query available, calling search API: {state['search_query']}")
            data = await self._retry_on_failure(get_serpapi_search_result, user_query=state['search_query'].search_queries[0])

            return {"search_result": data}

        else:
            log.info("No search query in state! Returning empty search result.")
            return {"search_result": {}, "search_query": SearchQuery()}

    def custom_tool_condition(self, state: ShoppingAgentState):
        """
        Define custom conditions to determine if a tool should be called based on the state.
        This is evaluated dynamically as part of the state graph.
        """
        if isinstance(state, list):
            ai_message = state[-1]
        elif isinstance(state, dict) and (messages := state.get("messages", [])):
            ai_message = messages[-1]
        elif messages := getattr(state, "messages", []):
            ai_message = messages[-1]
        else:
            raise ValueError(f"No messages found in input state to tool_edge: {state}")

        if hasattr(ai_message, "additional_kwargs") and ai_message.additional_kwargs.get(
                "tool_calls", None) is not None:
            return "tools"
        return END

    def get_search_agent(self):
        """
        Build the search agent state graph with defined actions and tools.
        The agent will decide whether to generate a query, fetch results, or end.
        """
        search_graph_builder = StateGraph(ShoppingAgentState)

        search_graph_builder.add_node("tools", ToolNode(self.search_query_tools))
        search_graph_builder.add_node("assistant", self.assistant)
        search_graph_builder.add_node("get_google_shopping_results", self.fetch_google_shopping_results)

        search_graph_builder.add_edge(START, "assistant")
        search_graph_builder.add_conditional_edges("assistant", self.custom_tool_condition, ["tools", END])
        search_graph_builder.add_edge("tools", "get_google_shopping_results")
        search_graph_builder.add_edge("get_google_shopping_results", END)

        search_graph = search_graph_builder.compile(checkpointer=MemorySaver())
        return search_graph

    def visualize(self):
        """
        Visualize the search agent state graph as a base64 PNG image.
        This allows users to see the structure of the agent's decision-making process.
        """
        png_image = self.search_graph.get_graph(xray=True).draw_mermaid_png()
        # Convert the PNG bytes to a base64 string
        buffered = BytesIO(png_image)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        log.info("Returning Image Base64")
        return {"image_base64": f"data:image/png;base64,{img_str}"}

    async def _retry_on_failure(self, func, *args, retries=MAX_RETRY_ATTEMPTS, delay=RETRY_DELAY, **kwargs):
        """
        Retry a function call in case of failure, with exponential backoff.
        """
        attempt = 0
        while attempt < retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                attempt += 1
                log.error(f"Attempt {attempt} failed for function {func.__name__} with error: {e}")
                if attempt >= retries:
                    log.error(f"Max retry attempts reached for {func.__name__}, giving up.")
                    raise
                log.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)

    def handle_external_error(self, error_message: str):
        """
        Handle errors from external services (e.g., search API or LLM) gracefully.
        """
        log.error(f"External service error: {error_message}")
        return {"error": error_message}

    def track_performance(self, start_time: float):
        """
        Log the performance and time taken to complete operations.
        """
        elapsed_time = time.time() - start_time
        log.info(f"Operation completed in {elapsed_time:.2f} seconds.")

    def get_state_graph(self):
        """
        Provides the state graph for the agent, which describes the flow of operations.
        """
        return self.search_graph
