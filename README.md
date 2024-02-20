
# Swisscom Coding Challenge

## Project Overview

When initiating this project, a critical decision was required regarding the architectural approach to handle client requests and node communication. Two potential methods were considered:

1.  **Asynchronous Request Handling**: This method involves receiving requests from the client, then asynchronously sending the appropriate requests to various nodes using the `httpx.AsyncClient` feature. Responses are collected, and based on the information, decisions are made whether to initiate rollback actions. This approach, however, presents challenges as increasing the number of nodes may lead to a higher likelihood of encountering `TimeoutException` due to potential rollback scenarios, despite the asynchronous request handling.

2.  **Queue-Based Processing**: This method entails receiving requests from clients and placing them into a queue. Workers then process these queued requests. In the event of a rollback scenario, additional messages are added to the queue. This approach allows for the immediate return of a `task_id` to the client, enabling them to inquire about the status of their task at their convenience.

After careful consideration, the second approach was selected due to its scalability and robustness in handling potential rollback scenarios.

## Workflow Description

The workflow implemented in this project is as follows:

- Upon receiving a request, it is queued, and a `task_id` is immediately returned to the client.

- A worker retrieves the request from the queue and initiates a process, marking the task's state in Redis for tracking.

- The worker then proceeds to create or delete groups on the nodes synchronously.

- If an error occurs during this process, the worker halts the creation/deletion process and generates a rollback message, including data on the processed nodes. This enables a rollback on the affected nodes if necessary.

- The worker retrieves the rollback message from the queue and begins sending the appropriate requests to the nodes (using information stored in Redis).

- In the case of an error, the worker attempts retries up to a maximum count specified by an environment variable.

- Should errors persist beyond the retry limit, the message is sent to a dead-letter queue for further action, which can be defined based on specific requirements.

- Upon successful rollback, the worker updates the nodes' data in Redis.

- If no nodes data remain, the corresponding key is removed from Redis.

This structured approach ensures efficient handling of requests and robust management of errors and rollbacks.

## API Documentation

This FastAPI application facilitates the asynchronous creation and deletion of groups on nodes, leveraging Celery and RabbitMQ for task management. The API allows for the submission of group creation and deletion tasks, as well as querying the status of these tasks.

### Version: 1.0.0

### Endpoints

#### Create Group

-  **POST**  `/groups/create`

-  **Summary**: Create a group with the specified `group_id`.

-  **Request Body** (required): JSON object specifying the group to create.

- Schema: `CreateGroup`

- Example:

```json
{
   "group_id": "test-group-1"
}
```
#### Delete Group
-  **POST**  `/groups/delete`
-  **Summary**: Delete a group with the specified `group_id`.
-  **Request Body** (required): JSON object specifying the group to delete.
- Schema: `DeleteGroup`
- Example:
```json
{
   "group_id": "test-group-1"
}
```
#### Get Task Status
-  **GET**  `/groups/task/{task_id}`
-  **Summary**: Returns the status of the submitted task.
-  **Parameters**:
-  `task_id` (path, required): The ID of the task to query.
 
## Configuration

The application's behavior is configured through environment variables. These variables can be set in your environment or defined in a `.env` file. The `config` function is used to load these variables, providing a default value where applicable. Below is a list of the environment variables used by the application:
You can also use `cp .env.example .env` command to create an .env file from the example template.

-  `CELERY_BROKER_URL`: URL for the Celery message broker (e.g., RabbitMQ). Must be specified in the environment or `.env` file.
	- Example: `CELERY_BROKER_URL=amqp://guest:guest@localhost/`

-  `CELERY_RESULT_BACKEND`: Backend used to store task results (e.g., Redis). Must be specified in the environment or `.env` file.
	- Example: `CELERY_RESULT_BACKEND=redis://localhost:6379/0`
	- 
-  `CELERY_DEFAULT_RETRY_DELAY`: Default delay (in seconds) before retrying a failed task. If not set, defaults to `10`.
	- Example: `CELERY_DEFAULT_RETRY_DELAY=10`

-  `CELERY_DEFAULT_MAX_RETRIES`: Maximum number of retries for a failed task. If not set, defaults to `3`.
	- Example: `CELERY_DEFAULT_MAX_RETRIES=3`

-  `REDIS_HOST`: Hostname of the Redis server. Defaults to `"localhost"` if not specified.
	- Example: `REDIS_HOST=localhost`

-  `REDIS_PORT`: Port on which the Redis server is running. Defaults to `6379` if not specified.
	- Example: `REDIS_PORT=6379`

-  `REDIS_DB`: Database number to use on the Redis server. Defaults to `0` if not specified.
	- Example: `REDIS_DB=0`

To configure these variables, either set them directly in your operating system's environment, or define them in a `.env` file at the root of your project directory. The `config` function will automatically load the values from the `.env` file if it is present.

## Installation

This project supports both Docker Compose for local development and Kubernetes for more robust deployment options. Below are the instructions for both methods.
  
### Using Docker Compose
#### Prerequisites
- Docker
- Docker Compose

#### Steps
1.  **Clone the Repository**
```shell
git clone https://github.com/onurceri/swisscom-coding-challenge
cd swisscom-coding-challenge
```

2.  **Build and Run with Docker Compose**
```shell
docker-compose up --build
```
This will build the Docker images and start the containers.

3.  **Accessing the Application**
The FastAPI application will be accessible at `http://localhost:8000`.

### Using Kubernetes (kubectl)
#### Prerequisites
- Kubernetes cluster or Minikube
- kubectl configured to communicate with your cluster

#### Steps
1.  **Clone the Repository**
```shell
git clone https://github.com/onurceri/swisscom-coding-challenge
cd swisscom-coding-challenge
```
2.  **Prepare Environment**
First, ensure Minikube is running:
```shell
minikube start
```
Run this command to configure your shell to use Minikube's Docker daemon:

```shell
eval $(minikube docker-env)
```

3. **Build Docker Image**
```shell
docker build -t fastapi-app:latest .
```  

  4. **Deploy Manifests to Minikube**
```shell
cd manifests/base

kubectl apply -f deployments/
kubectl apply -f services/
```  
 5. **Verify the Deployments and Services**
```shell
kubectl get deployments
kubectl get services
```

8.  **Accessing the Application**
```shell
minikube service fastapi-app-service --url
```

9. **Creating NODES for Help to Test**
You can use https://github.com/onurceri/mock-node-api repository to create NODES to mock node api response's.

## Running Tests
To ensure the reliability of the application, follow these steps to run the automated test suite:

### Prerequisites
- Python
- Pip

### Steps
1.  **Activate the Virtual Environment (Optional)**
```shell
python -m venv venv source venv/bin/activate
# On Windows, use venv\Scripts\activate
```

2.  **Install Dependencies**
```shell
pip install -r requirements.txt
```

3.  **Run the Tests**

```shell
pytest
```
This will execute all tests in the `tests` directory.
