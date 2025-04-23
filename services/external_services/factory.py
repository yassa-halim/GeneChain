import heapq
import os
import importlib
import logging
from threading import Lock, Event
from pympler import asizeof
from pyopenagi.manager.manager import AgentManager


class AgentFactory:
    def __init__(self, agent_log_mode, agent_manager_url="https://bioarchive.io"):
        self.agent_log_mode = agent_log_mode
        self.manager = AgentManager(agent_manager_url)
        self.current_agents = {}
        self.current_agents_lock = Lock()
        self.terminate_signal = Event()
        self.logger = logging.getLogger(__name__)

        logging.basicConfig(level=logging.INFO)

    def snake_to_camel(self, snake_str):
        components = snake_str.split("_")
        return "".join(x.title() for x in components)

    def list_agents(self):
        agent_list = self.manager.list_available_agents()
        self.logger.info("Listing available agents:")
        for agent in agent_list:
            self.logger.info(agent)

    def load_agent_instance(self, compressed_name: str):
        try:
            author, name = compressed_name.split("/")
            module_name = ".".join(["pyopenagi", "agents", author, name, "agent"])
            class_name = self.snake_to_camel(name)
            agent_module = importlib.import_module(module_name)
            return getattr(agent_module, class_name)
        except (ImportError, AttributeError, ValueError) as e:
            self.logger.error(f"Local loading failed for {compressed_name}: {str(e)}")
            name_split = compressed_name.split('/')
            return self.manager.load_agent(*name_split)

    def activate_agent(self, agent_name: str, task_input):
        try:
            agent_class = self.load_agent_instance(agent_name)
        except Exception as e:
            self.logger.error(f"Both local and remote loading failed for {agent_name}: {str(e)}")
            raise

        try:
            agent = agent_class(
                agent_name=agent_name,
                task_input=task_input,
                log_mode=self.agent_log_mode
            )
            with self.current_agents_lock:
                self.current_agents[agent_name] = agent

            return agent
        except Exception as e:
            self.logger.error(f"Error activating agent {agent_name}: {str(e)}")
            raise

    def run_agent(self, agent_name, task_input):
        try:
            agent = self.activate_agent(agent_name=agent_name, task_input=task_input)
            output = agent.run()
            self.logger.info(f"Agent {agent_name} execution complete.")
            return output
        except Exception as e:
            self.logger.error(f"Error running agent {agent_name}: {str(e)}")
            return None

    def print_agent_info(self):
        headers = ["Agent Name", "Created Time", "Status", "Memory Usage"]
        data = []

        with self.current_agents_lock:
            for agent_name, agent in self.current_agents.items():
                created_time = agent.created_time
                status = agent.status
                memory_usage = f"{asizeof.asizeof(agent)} bytes"
                data.append([agent_name, created_time, status, memory_usage])

        self.print_table(headers=headers, data=data)

    def print_table(self, headers, data):
        column_widths = [
            max(len(str(row[i])) for row in [headers] + data) for i in range(len(headers))
        ]

        row_format = " | ".join(f"{{:<{width}}}" for width in column_widths)
        table_width = sum(column_widths) + len(headers) * 3 - 3

        self.logger.info("+" + "-" * table_width + "+")
        self.logger.info(row_format.format(*headers))
        self.logger.info("=" * table_width)

        for row in data:
            self.logger.info(row_format.format(*row))
            self.logger.info("-" * table_width)

        self.logger.info("+" + "-" * table_width + "+")

    def deactivate_agent(self, agent_name):
        with self.current_agents_lock:
            if agent_name in self.current_agents:
                agent = self.current_agents.pop(agent_name)
                agent.deactivate()
                self.logger.info(f"Agent {agent_name} deactivated.")
            else:
                self.logger.warning(f"Agent {agent_name} not found for deactivation.")

    def get_memory_usage(self):
        total_memory = 0
        with self.current_agents_lock:
            for agent in self.current_agents.values():
                total_memory += asizeof.asizeof(agent)
        return total_memory

    def terminate(self):
        self.logger.info("Terminating agent factory.")
        self.terminate_signal.set()
        with self.current_agents_lock:
            for agent_name in list(self.current_agents):
                self.deactivate_agent(agent_name)


class Agent:
    def __init__(self, agent_name, task_input, log_mode):
        self.agent_name = agent_name
        self.task_input = task_input
        self.log_mode = log_mode
        self.status = "inactive"
        self.created_time = "N/A"
        self.memory_usage = 0

    def run(self):
        self.status = "running"
        # Implement the actual agent task execution here
        self.created_time = "2025-01-19"
        self.status = "completed"
        return {"status": "completed"}

    def deactivate(self):
        self.status = "deactivated"


if __name__ == "__main__":
    factory = AgentFactory(agent_log_mode="info")
    factory.list_agents()

    agent_output = factory.run_agent("agent_name", task_input={"input_data": "value"})
    factory.print_agent_info()
    factory.terminate()
