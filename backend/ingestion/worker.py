from celery import Celery
from ..config import settings


celery_app = Celery(
    "project1_celery",  # just application name
    broker=settings().REDIS_URL,  # delay() stores here
    backend=settings().REDIS_URL,  # task result is stored here, return value of fucntion called
    include=[
        "backend.ingestion.tasks"
    ],  # file where tasks are there, need before runtime
)

celery_app.conf.update(
    # Serialization — JSON only, never pickle which is defualt (security issue)
    # pickle.loads/dumps -> convert anything into bytes, so might also convert malacious code.
    task_serializer="json",  # when using delay() to store task in redis
    result_serializer="json",  # return value of func when run by worker stored in redis as json
    accept_content=[
        "json"
    ],  # when worker picks up task from redis to run, accepts json
    # suppose one worker process crashes, could not even tell redis about this through ack_late
    # redis will handover this task if it doesnt listen ack form that worker process in this time.
    broker_transport_options={"visibility_timeout": 3600},  # 1hr
    # must be large enough than task processing time,
    #  else two workers would be doing duplicate tasks
    task_acks_late=True,  # this make sure when task completed only then worker send ack
    task_reject_on_worker_lost=True,  # if recived ack_late, handover to another by requeue
    # One task per worker process, else celery might assign many to one worker, others sit idle
    worker_prefetch_multiplier=1,
    # this task will go to ingestion queue.
    task_routes={
        "ingestion.tasks.process_document_task": {"queue": "ingestion"},
    },
    # Retry policy applied to all tasks, else use default
    task_default_retry_delay=30,  # seconds
    task_max_retries=3,
)


#  Idempotent delivery: at-least-once with ack-on-success
# celery gurantees with these config that a task will not be silently lost
# and it will retry it
# but what if task completely sucessfully then some problem occurs
# and redis handover this task to another worker, task will run twice.
# thats why our task code neeeds to be idompotent,
# means running it multiple times would give same final state, as if run only once.
# say if task updates a balance, then balance might be updated twice.
