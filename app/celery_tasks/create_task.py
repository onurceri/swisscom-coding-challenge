import json
import logging

import httpx

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

REDIS_KEY_PREFIX = "rollback_create_group_"


def _is_rollback_needed(node: str, group_id: str, response: httpx.Response) -> bool:
    """
    Determines if rollback is needed based on group creation response.

    Args:
        node (str): Name of the node.
        group_id (str): Group ID.
        response (httpx.Response): Response object from group creation.

    Returns:
        bool: True if rollback is needed, False otherwise.
    """

    if response.status_code == 400:
        # Check if group already exists (rollback needed if non-existent)
        get_group_response = node_client.get_group(node, group_id)
        return get_group_response.status_code != 200
    elif response.status_code >= 500:
        # Rollback needed if node error occurred
        return True
    return False


@celery_app.task(name="app.celery_tasks.create_task.create_group")
def create_group(group_id: str):
    """
    Creates a group on all nodes.

    Args:
        group_id (str): ID of the group to create.
    """

    rollback_key = f"{REDIS_KEY_PREFIX}{group_id}"
    # Skip creation if rollback data exists (indicating previous failure)
    if redis_client.exists(rollback_key):
        logger.info(f"Rollback data exists for group {group_id}, skipping creation.")
        return

    # Set empty rollback data to lock creation
    redis_client.set(f"{rollback_key}", json.dumps([]))

    nodes_processed = []
    for node in HOSTS:
        response = node_client.create_group(node, group_id)
        if _is_rollback_needed(node, group_id, response):
            logger.info(f"Rollback needed for group {group_id} on node {node}.")
            trigger_rollback(group_id, nodes_processed)
            break

        logger.info(f"{node} processed. Group {group_id} created successfully.")
        nodes_processed.append(node)

    # If all nodes processed, delete rollback data
    if len(nodes_processed) == len(HOSTS):
        redis_client.delete(f"{rollback_key}")


def trigger_rollback(group_id: str, nodes_processed: list) -> None:
    """
    Triggers rollback for group creation on specified nodes.

    Args:
        group_id (str): ID of the group to rollback.
        nodes_processed (list): List of nodes that need rollback.
    """

    rollback_key = f"{REDIS_KEY_PREFIX}{group_id}"
    redis_value = json.dumps({"group_id": group_id, "nodes": nodes_processed})
    redis_client.set(
        rollback_key,
        redis_value,
        ex=60 * 60,
    )
    logger.info(
        f"Rollback data set on redis. Key: {rollback_key}, Value: {redis_value}"
    )

    for node in nodes_processed:
        celery_app.send_task(
            "app.celery_tasks.create_task.rollback_create_group",
            kwargs={"group_id": group_id, "node": node},
        )
        logger.info(f"Rollback task sent for group {group_id} on node {node}.")


@celery_app.task(
    name="app.celery_tasks.create_task.rollback_create_group",
    default_retry_delay=CELERY_DEFAULT_RETRY_DELAY,
    max_retries=CELERY_DEFAULT_MAX_RETRIES,
    acks_late=True,
)
def rollback_create_group(group_id: str, node: str):
    """
    Rolls back group creation on a specific node.

    Args:
        group_id (str): ID of the group to rollback.
        node (str): Name of the node to rollback the group on.
    """

    rollback_key = f"{REDIS_KEY_PREFIX}{group_id}"
    rollback_item = redis_client.get(rollback_key)
    if not rollback_item:
        logger.info(
            f"Rollback data doesn't exist for group {group_id}, skipping rollback. Node: {node}"
        )
        return

    rollback_item_data = json.loads(rollback_item)
    if node not in rollback_item_data["nodes"]:
        logger.info(
            f"Node {node} not in rollback data for group {group_id}, skipping rollback."
        )
        return

    # Delete group on node
    response = node_client.delete_group(node, group_id)
    if response.status_code != 200:
        _handle_failed_rollback(group_id, node)
    else:
        _update_rollback_data(group_id, node)


def _handle_failed_rollback(group_id: str, node: str) -> None:
    """
    Handles retries or dead-lettering for failed group deletion.

    Args:
        group_id (str): Group ID.
        node (str): Name of the node.
    """

    if rollback_create_group.request.retries != rollback_create_group.max_retries:
        rollback_create_group.retry(exc=Exception("Failed to delete group on node."))
    else:
        redis_client.delete(f"rollback_create_group_{group_id}")
        celery_app.send_task(
            "app.celery_tasks.dead_letter_task.process_dead_letter",
            kwargs={
                "group_id": group_id,
                "node": node,
                "task": "rollback_create_group",
            },
        )


def _update_rollback_data(group_id: str, node: str) -> None:
    """
    Updates rollback data after successful group deletion.

    Args:
        group_id (str): ID of the group.
        node (str): Name of the node.
    """

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
    
    rollback_data["nodes"].remove(node)
    if not rollback_data["nodes"]:
        redis_client.delete(rollback_key)
    else:
        redis_client.set(rollback_key, json.dumps(rollback_data))
