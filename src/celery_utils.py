import functools
import ssl
from celery import current_app as current_celery_app, shared_task
from celery.result import AsyncResult
from celery.utils.time import get_exponential_backoff_interval
from src.config import settings

ssl_options = {
    "ssl_cert_reqs": ssl.CERT_REQUIRED,  # ⚠️ Insecure, use CERT_REQUIRED in production
}

def create_celery():
    celery_app = current_celery_app
    
    celery_app.conf.update(
        namespace="CELERY",
        broker_url=settings.CELERY_BROKER_URL,  # rediss://...
        result_backend=settings.CELERY_RESULT_BACKEND,  # rediss://...
        #broker_use_ssl=ssl_options,
        #redis_backend_use_ssl=ssl_options,
        broker_connection_retry_on_startup=True,
        task_default_retry_delay=5,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_reject_on_worker_lost=True,
        broker_transport_options={
                "global_keyprefix": "lafaom:" 
            },
        result_backend_transport_options={
                "global_keyprefix": "lafaom:" 
            },
        task_default_queue="lafaom_default",
        task_queues={
            "lafaom_default": {
                "exchange": "lafaom",
                "routing_key": "lafaom.default",
            },
        }
        # Other configurations
    )


    return celery_app


def get_task_info(task_id):
    """
    return task info according to the task_id
    """
    task = AsyncResult(task_id)
    

    if task.state == "FAILURE":
        
        response = {
            "state": task.state,
            "error": str(task.result)
        }
    else:
        response = {
            "state": task.state,
            "result": task.result,
        }
    return response


class custom_celery_task:

    EXCEPTION_BLOCK_LIST = (
        IndexError,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    )

    def __init__(self, *args, **kwargs):
        self.task_args = args
        self.task_kwargs = kwargs

    def __call__(self, func):
        @functools.wraps(func)
        def wrapper_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except self.EXCEPTION_BLOCK_LIST:
                # do not retry for those exceptions
                raise
            except Exception as e:
                # here we add Exponential Backoff just like Celery
                countdown = self._get_retry_countdown(task_func)
                raise task_func.retry(exc=e, countdown=countdown)

        task_func = shared_task(*self.task_args, **self.task_kwargs)(wrapper_func)
        return task_func

    def _get_retry_countdown(self, task_func):
        retry_backoff = int(
            max(1.0, float(self.task_kwargs.get('retry_backoff', True)))
        )
        retry_backoff_max = int(
            self.task_kwargs.get('retry_backoff_max', 600)
        )
        retry_jitter = self.task_kwargs.get(
            'retry_jitter', True
        )

        countdown = get_exponential_backoff_interval(
            factor=retry_backoff,
            retries=task_func.request.retries,
            maximum=retry_backoff_max,
            full_jitter=retry_jitter
        )

        return countdown
