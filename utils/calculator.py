import os
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from typing import List, Dict, Any, Tuple
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_agent_tasks(agent_name: str) -> List[str]:
    """Load tasks for the given agent from file."""
    file_path = os.path.join(os.getcwd(), "pyopenagi/data/agent_tasks", f"{agent_name}_task.txt")
    if not os.path.exists(file_path):
        logger.error(f"Task file for agent {agent_name} not found: {file_path}")
        return []
    with open(file_path) as f:
        task_inputs = f.readlines()
        return task_inputs

def calculate_improvement(sequential: float, concurrent: float) -> float:
    """Calculate the performance improvement between sequential and concurrent."""
    if sequential == 0:
        logger.warning("Sequential time is 0, cannot calculate improvement.")
        return 0
    return (sequential - concurrent) / sequential * 100

def compute_metrics(data: List[float]) -> Dict[str, float]:
    """Compute average, 90th percentile, and 99th percentile from data."""
    if not data:
        return {'avg': 0, 'p90': 0, 'p99': 0}
    return {
        'avg': np.mean(data),
        'p90': np.percentile(data, 90),
        'p99': np.percentile(data, 99)
    }

def get_numbers_concurrent(agent_list: List[Tuple[str, int]], agent_factory: Any, agent_thread_pool: ThreadPoolExecutor) -> Dict[str, Any]:
    """Calculate metrics for agents using concurrent execution."""
    agent_tasks = []
    stats = {
        'turnaround_times': [],
        'waiting_times': [],
        'request_waiting_times': [],
        'request_turnaround_times': []
    }

    # Load tasks for agents and submit them to the thread pool
    for agent_name, agent_num in agent_list:
        task_inputs = load_agent_tasks(agent_name=agent_name)[0:agent_num]
        for task_input in task_inputs:
            agent_task = agent_thread_pool.submit(agent_factory.run_agent, agent_name, task_input)
            agent_tasks.append(agent_task)

    # Collect results from completed tasks
    for result in as_completed(agent_tasks):
        try:
            output = result.result()
            stats['waiting_times'].append(output["agent_waiting_time"])
            stats['turnaround_times'].append(output["agent_turnaround_time"])
            stats['request_waiting_times'].extend(output["request_waiting_times"])
            stats['request_turnaround_times'].extend(output["request_turnaround_times"])
        except Exception as e:
            logger.error(f"Error processing agent task: {e}")

    # Compute metrics
    metrics = {
        'agent_waiting_time': compute_metrics(stats['waiting_times']),
        'agent_turnaround_time': compute_metrics(stats['turnaround_times']),
        'request_waiting_time': compute_metrics(stats['request_waiting_times']),
        'request_turnaround_time': compute_metrics(stats['request_turnaround_times'])
    }

    return metrics

def get_numbers_sequential(agent_list: List[Tuple[str, int]], agent_factory: Any) -> Dict[str, Any]:
    """Calculate metrics for agents using sequential execution."""
    stats = {
        'turnaround_times': [],
        'waiting_times': [],
        'request_waiting_times': [],
        'request_turnaround_times': []
    }

    accumulated_time = 0
    # Load tasks for agents and process them one by one
    for agent_name, agent_num in agent_list:
        task_inputs = load_agent_tasks(agent_name=agent_name)[0: agent_num]
        for task_input in task_inputs:
            output = agent_factory.run_agent(agent_name=agent_name, task_input=task_input)

            # Adjust times based on the accumulated time
            agent_turnaround_time = output["agent_turnaround_time"] + accumulated_time
            agent_waiting_time = output["agent_waiting_time"] + accumulated_time
            request_waiting_times = [x + accumulated_time for x in output["request_waiting_times"]]
            request_turnaround_times = [x + accumulated_time for x in output["request_turnaround_times"]]

            stats['turnaround_times'].append(agent_turnaround_time)
            stats['waiting_times'].append(agent_waiting_time)
            stats['request_waiting_times'].extend(request_waiting_times)
            stats['request_turnaround_times'].extend(request_turnaround_times)

            accumulated_time += (agent_turnaround_time - agent_waiting_time)

    # Compute metrics
    metrics = {
        'agent_waiting_time': compute_metrics(stats['waiting_times']),
        'agent_turnaround_time': compute_metrics(stats['turnaround_times']),
        'request_waiting_time': compute_metrics(stats['request_waiting_times']),
        'request_turnaround_time': compute_metrics(stats['request_turnaround_times'])
    }

    return metrics

def comparison(concurrent_metrics: Dict[str, Any], sequential_metrics: Dict[str, Any]) -> None:
    """Compare sequential and concurrent metrics, calculating improvements."""
    logger.info("**** Improvement Analysis Starts ****")

    improvements = {}
    for key in concurrent_metrics.keys():
        concurrent_avg = concurrent_metrics[key]['avg']
        sequential_avg = sequential_metrics[key]['avg']
        improvements[key + '_avg_improv'] = calculate_improvement(sequential_avg, concurrent_avg)

        concurrent_p90 = concurrent_metrics[key]['p90']
        sequential_p90 = sequential_metrics[key]['p90']
        improvements[key + '_p90_improv'] = calculate_improvement(sequential_p90, concurrent_p90)

        concurrent_p99 = concurrent_metrics[key]['p99']
        sequential_p99 = sequential_metrics[key]['p99']
        improvements[key + '_p99_improv'] = calculate_improvement(sequential_p99, concurrent_p99)

    # Print improvements
    for improv_key, improv_value in improvements.items():
        logger.info(f"Improvement of {improv_key}: {improv_value:.2f}%")

def run_performance_comparison(agent_list: List[Tuple[str, int]], agent_factory: Any, agent_thread_pool: ThreadPoolExecutor) -> None:
    """Run both sequential and concurrent calculations and compare the results."""
    # Sequential
    logger.info("Running sequential tasks...")
    sequential_metrics = get_numbers_sequential(agent_list, agent_factory)
    
    # Concurrent
    logger.info("Running concurrent tasks...")
    concurrent_metrics = get_numbers_concurrent(agent_list, agent_factory, agent_thread_pool)
    
    # Compare results
    comparison(concurrent_metrics, sequential_metrics)
