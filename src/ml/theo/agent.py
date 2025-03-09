import redis
import mlflow
import asyncio
import psycopg2
import pickle
import hashlib
from collections import deque
from multiprocessing import Pool, Queue, Process
import time
import logging
from typing import Union, Dict, List, Tuple, Any, TypeAlias, Iterable

from ml.theo.preprocessing import preprocess

Id: TypeAlias = str
class TheoAgent:
    def __init__(self, num_workers: int = None, redis_host: str = 'localhost', redis_port: int = 6379):
        self.num_workers = num_workers
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.r = redis.Redis(self.redis_host, self.redis_port)
        # task kwargs 
        # tasked with receiving training tasks from client(s)
        self.task_queue = asyncio.PriorityQueue()
        # communicates with `Worker` processes
        self.communication_queue = Queue()
        # sends models as they are trained back to client(s)
        self.model_queue = asyncio.Queue()
        self.pool = Pool(num_workers)
        logging.debug("Initialized TheoAgent")

    def set_task_kwargs(self, **task_kwargs):
        self.task_kwargs = task_kwargs
        

    def add_task(self, market_id: str, make_priority: bool = False, **task_kwargs) -> Id:
        t = str(int(time.time()))
        task_id = hashlib.sha256((market_id + t).encode(), usedforsecurity=False).hexdigest()
        priority = 0 if make_priority else 1
        self.task_queue.put((priority, (market_id, task_id, task_kwargs)))
        return task_id

    async def launch_workers(self):
        while True:
            priority, (market_id, task_id, task_kwargs) = await self.task_queue.get()
            task_arguments = {
                "task_arguments": self.task_kwargs,
                "market_id": market_id,
                "communication_queue": self.communication_queue,
                "redis_host": self.redis_host,
                "redis_port": self.redis_port,
                "mlflow_tracking_uri": self.mlflow_tracking_uri, 
                "mlflow_experiment_name": task_id, 
                "postgres_conn_params": dict
            }
            # process = Process()
            self.pool.apply_async(self.__worker, kwds=task_arguments)

    async def handle_results(self):
        loop = asyncio.get_running_loop()
        while True:
            try:
                result = await loop.run_in_executor(None, self.communication_queue.get)
                market_id = result.get("market_id")
                model_bytes = result.get("model")
                if market_id and model_bytes:
                    logging.info(f"Received model for {market_id}")
                    await self.model_queue.put((market_id, model_bytes))  # Put model in queue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error handling result: {e}")

    async def get_models(self):
        while True:
            try:
                market_id, model_bytes = await self.model_queue.get()
                yield market_id, model_bytes
            except asyncio.CancelledError:
                break
    
    @staticmethod
    def __worker(
            task_arguments: Dict[str, Any], 
            market_id: str,
            communication_queue: Queue, 
            redis_host: str, 
            redis_port: int, 
            mlflow_tracking_uri: str, 
            mlflow_experiment_name: str, 
            postgres_conn_params: dict
        ):
        """Processes a single task."""
        market_id = market_id
        run_id = task_arguments.get("run_id")
        time_range = task_arguments.get("time_range") #time_range is passed in the task_arguments
        last_preferred_model = task_arguments.get("past_model_id")

        if not market_id or not data or not run_id:
            logging.error("Task arguments missing market_id, data, or run_id.")
            return

        run_name = f"{market_id}_{run_id}"
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        with mlflow.start_run(run_name=run_name, experiment_name=mlflow_experiment_name):
            mlflow.set_tag("market_id", market_id)
            try:
                # 1. retrieve data from TSDB
                conn = psycopg2.connect(**postgres_conn_params)
                cursor = conn.cursor()
                query = f"SELECT * FROM your_tsdb_table WHERE market_id = '{market_id}' AND timestamp BETWEEN '{time_range[0]}' AND '{time_range[1]}';"
                cursor.execute(query)
                data = cursor.fetchall()
                # 2. preprocess data
                preprocessed_data = preprocess(data)
                # 3. train model
                res_model = None
                # 4. cross validate model 
                redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0) #Redis connection per task.
            except Exception as e:
                logging.error(f"Error processing task for {market_id}: {e}")
            finally:
                _t = time.time()
                status = 'success'
                errors = []
                communication_queue.put({"market_id": market_id, "timestamp": _t, "status": status, errors: errors})