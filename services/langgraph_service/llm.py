import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOllama
from langchain_openai import ChatOpenAI
from utils.helper_functions import get_custom_logger

# Load environment variables
load_dotenv()

log = get_custom_logger(name=__name__)

# Constants for model configurations
SUPPORTED_MODELS = ["groq", "ollama", "openai"]
DEFAULT_MODEL = "groq"

# Default values for LLM models
DEFAULT_TEMPERATURE = 0


def load_llm_config(model: str):
    """
    Load LLM configuration for the specified model from environment variables.
    If the configuration does not exist, raises an error.
    """
    llm_config_env = f"LLM_CONFIG_{model.upper()}"
    env_value = os.environ.get(llm_config_env)

    if not env_value:
        raise ValueError(f"Invalid or missing environment variable for model '{model}': {llm_config_env}")

    model_details = env_value.split(",")
    if len(model_details) != 2:
        raise ValueError(f"Environment variable '{llm_config_env}' should contain model name and API key, separated by a comma.")

    return model_details[0], model_details[1]


def get_llm(model: str = DEFAULT_MODEL):
    """
    Retrieve the language model based on the provided model name.
    Supports 'groq', 'ollama', and 'openai'.
    """
    model = model.lower()

    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Model '{model}' is not supported. Supported models are: {', '.join(SUPPORTED_MODELS)}.")

    log.info(f"Initializing {model} LLM...")

    try:
        model_name, api_key = load_llm_config(model)
        llm = None

        if model == "groq":
            llm = ChatGroq(api_key=api_key, model_name=model_name, temperature=DEFAULT_TEMPERATURE)

        elif model == "ollama":
            llm = ChatOllama(model=model_name)

        elif model == "openai":
            llm = ChatOpenAI(api_key=api_key, model=model_name, temperature=DEFAULT_TEMPERATURE)

        log.info(f"Successfully initialized {model} LLM: {model_name}")

    except ValueError as e:
        log.error(f"Error loading LLM configuration: {e}")
        raise

    except Exception as e:
        log.error(f"Unexpected error while initializing the model: {e}")
        raise

    return llm


def validate_environment_variables():
    """
    Validates that the necessary environment variables are set for each supported model.
    """
    missing_vars = []
    for model in SUPPORTED_MODELS:
        llm_config_env = f"LLM_CONFIG_{model.upper()}"
        if not os.environ.get(llm_config_env):
            missing_vars.append(llm_config_env)

    if missing_vars:
        raise EnvironmentError(f"The following environment variables are missing: {', '.join(missing_vars)}")

    log.info("All necessary environment variables are set.")


def get_model_details(model: str):
    """
    Retrieve details about the model (name, API key) from environment variables.
    """
    try:
        model_name, api_key = load_llm_config(model)
        return model_name, api_key
    except ValueError as e:
        log.error(f"Error fetching model details: {e}")
        raise


def test_llm_connection(model: str):
    """
    Perform a basic test to ensure the LLM can be instantiated and connected successfully.
    This helps in verifying that the API key and model configurations are correct.
    """
    log.info(f"Testing connection to {model} model...")

    try:
        llm = get_llm(model)
        # Perform a simple test query if supported (for models that support basic queries)
        test_query = "Hello, world!"
        response = llm.chat([test_query])
        log.info(f"Test response from {model}: {response}")
        return True

    except Exception as e:
        log.error(f"Failed to connect to {model}: {e}")
        return False


def get_llm_list():
    """
    Retrieve a list of all available LLM models and their configurations from environment variables.
    """
    model_list = {}

    for model in SUPPORTED_MODELS:
        try:
            model_name, api_key = get_model_details(model)
            model_list[model] = {"model_name": model_name, "api_key": api_key}
        except ValueError:
            log.warning(f"Missing configuration for {model}")

    return model_list


def log_llm_status(model_name: str, status: str):
    """
    Log the status of the LLM (e.g., initialized, failed).
    """
    log.info(f"LLM '{model_name}' status: {status}")


def fetch_model_metadata(model_name: str):
    """
    Fetch additional metadata for the LLM from an external service or configuration.
    Placeholder for future use (e.g., model version, supported features).
    """
    log.info(f"Fetching metadata for model: {model_name}")
    # This could fetch version info, update status, etc. depending on the LLM's API.
    metadata = {"version": "1.0", "supported_features": ["chat", "summarize", "generate_text"]}
    log.info(f"Metadata for {model_name}: {metadata}")
    return metadata


class LLMHandler:
    """
    A class to encapsulate logic for handling multiple LLM models and configurations.
    It manages the retrieval, validation, and logging for different models.
    """

    def __init__(self):
        self.llms = {}

    def add_llm(self, model: str):
        """
        Add a new LLM to the handler by initializing and testing the connection.
        """
        try:
            self.llms[model] = get_llm(model)
            log_llm_status(model, "initialized")
        except Exception as e:
            log_llm_status(model, f"failed - {e}")

    def remove_llm(self, model: str):
        """
        Remove an LLM from the handler.
        """
        if model in self.llms:
            del self.llms[model]
            log_llm_status(model, "removed")
        else:
            log.warning(f"Attempted to remove {model}, but it wasn't in the handler.")

    def get_llm_instance(self, model: str):
        """
        Get the instance of a specified LLM model.
        """
        return self.llms.get(model)

    def test_all_connections(self):
        """
        Test the connection to all LLMs in the handler.
        """
        results = {}
        for model in self.llms:
            results[model] = test_llm_connection(model)
        return results


# Example usage:
if __name__ == "__main__":
    # Initialize LLM handler
    llm_handler = LLMHandler()

    # Add all supported models
    for model in SUPPORTED_MODELS:
        llm_handler.add_llm(model)

    # Test all LLM connections
    connection_results = llm_handler.test_all_connections()
    log.info(f"LLM connection test results: {connection_results}")

    # Example: Fetching LLM instance for OpenAI
    openai_llm = llm_handler.get_llm_instance("openai")
    if openai_llm:
        log.info("Successfully retrieved OpenAI LLM instance.")

    # Fetch and log metadata for Groq model
    metadata = fetch_model_metadata("groq")
    log.info(f"Groq model metadata: {metadata}")

