import json
import logging

from app.celery_tasks.celery_app import celery_app
from app.shared.redis_client import redis_client


logger = logging.getLogger(__name__)


@celery_app.task(name="app.celery_tasks.dead_letter_task.process_dead_letter")
def process_dead_letter(group_id: str, node: str, task: str):
    """
    Processes a dead letter identified by task name, group ID, and node.

    Args:
        task_name (str): Name of the task that failed.
        group_id (str): Group ID.
        node (str): Node where the task failed.

    Returns:
        None
    """
    rollback_key = f"{task}_{group_id}"

    # Retrieve rollback item from Redis
    rollback_item = redis_client.get(rollback_key)
    if rollback_item is None:
        logger.info(f"No rollback item found for {rollback_key}")
        return

    # Decode and validate rollback item
    try:
        rollback_item_data = json.loads(rollback_item)
        if "nodes" not in rollback_item_data:
            raise ValueError(f"Invalid rollback item format: {rollback_key}")
    except (json.JSONDecodeError, ValueError):
        logger.error(f"Failed to decode or validate rollback item: {rollback_key}")
        return

    if node in rollback_item_data["nodes"]:
        rollback_item_data["nodes"].remove(node)

        if not rollback_item_data["nodes"]:
            redis_client.delete(rollback_key)
            logger.info(f"Deleted {rollback_key} from Redis as no nodes are left.")
        else:
            redis_client.set(rollback_key, json.dumps(rollback_item_data))
            logger.info(f"Updated {rollback_key} in Redis with remaining nodes.")
    else:
        logger.info(f"Node {node} not found in rollback item nodes for {rollback_key}")
