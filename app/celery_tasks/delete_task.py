import json
import logging

from app.celery_tasks.celery_app import celery_app
from app.clients.node_client import NodeClient
from app.shared.redis_client import redis_client
from config.app_config import (
    CELERY_DEFAULT_MAX_RETRIES,
    CELERY_DEFAULT_RETRY_DELAY,
    HOSTS,
)

node_client = NodeClient()

logger = logging.getLogger(__name__)

REDIS_KEY_PREFIX = "rollback_delete_group_"


@celery_app.task(name="app.celery_tasks.delete_task.delete_group")
def delete_group(group_id: str):
    """
    Deletes a group on all nodes.

    Args:
        group_id (str): ID of the group to delete.

    Returns:
        None
    """

    nodes_processed = []
    for node in HOSTS:
        response = node_client.delete_group(node, group_id)
        if response.status_code == 200:
            logger.info(f"Group {group_id} deleted on {node}")
        elif response.status_code > 400:
            logger.error(
                f"Group {group_id} could not be deleted on {node}. Retrying..."
            )
            trigger_rollback(group_id, nodes_processed)
            break

        nodes_processed.append(node)


def trigger_rollback(group_id: str, nodes_processed: list):
    """
    Triggers rollback for group deletion on specified nodes.

    Args:
        group_id (str): ID of the group to rollback.
        nodes_processed (list): List of nodes that need rollback.
    """

    redis_key = f"{REDIS_KEY_PREFIX}{group_id}"
    redis_value = json.dumps({"group_id": group_id, "nodes": nodes_processed})
    redis_client.set(
        redis_key,
        redis_value,
        ex=60 * 60,  # 1 hour expiration
    )

    logger.info(f"Rollback data set on redis. Key: {redis_key}, Value: {redis_value}")

    for node in nodes_processed:
        celery_app.send_task(
            "app.celery_tasks.delete_task.rollback_delete_group",
            kwargs={"group_id": group_id, "node": node},
        )


@celery_app.task(
    name="app.celery_tasks.delete_task.rollback_delete_group",
    default_retry_delay=CELERY_DEFAULT_RETRY_DELAY,
    max_retries=CELERY_DEFAULT_MAX_RETRIES,
    acks_late=True,
)
def rollback_delete_group(group_id: str, node: str):
    """
    Rolls back group deletion on a specific node.

    Args:
        group_id (str): ID of the group to rollback.
        node (str): Name of the node to rollback the group on.
    """
    # Check if rollback data exists
    rollback_key = f"{REDIS_KEY_PREFIX}{group_id}"
    rollback_item = redis_client.get(rollback_key)
    if not rollback_item:
        logger.info(f"No rollback needed for group {group_id}.")
        return

    try:
        rollback_data = json.loads(rollback_item)
    except (json.JSONDecodeError, ValueError):
        logger.error(f"Failed to decode or validate rollback item: {rollback_key}")
        return

    if "group_id" not in rollback_data or "nodes" not in rollback_data:
        logger.error(f"Invalid rollback data for group {group_id}: {rollback_data}")
        return

    if node not in rollback_data["nodes"]:
        logger.info(
            f"Node {node} not in rollback data for group {group_id}, skipping rollback."
        )
        return

    response = node_client.create_group(node, group_id)
    if response.status_code == 201:
        rollback_data["nodes"].remove(node)
        if not rollback_data["nodes"]:
            redis_client.delete(f"{REDIS_KEY_PREFIX}{group_id}")
        else:
            redis_client.set(f"{REDIS_KEY_PREFIX}{group_id}", json.dumps(rollback_data))
        return

    if rollback_delete_group.request.retries != rollback_delete_group.max_retries:
        rollback_delete_group.retry(exc=Exception("Failed to create group on node."))
        return

    redis_client.delete(f"{REDIS_KEY_PREFIX}{group_id}")
    celery_app.send_task(
        "app.celery_tasks.dead_letter_task.process_dead_letter",
        kwargs={
            "group_id": group_id,
            "node": node,
            "task": "rollback_delete_group",
        },
    )
