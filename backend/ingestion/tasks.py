from fastapi import HTTPException
import logging
from celery import Task
from .worker import celery_app
from .storage import validate_mime_type
from .dependencies import get_boto3_client, s3_download_config

logger = logging.getLogger(__name__)


# _ means Internal class. Not intended for direct use.
class _BaseIngestionTask(Task):
    # This class is NOT itself a runnable task else celery would try to do run() func
    abstract = True

    # task_id or self.request.id are same
    # task_id fill by celery, unique for each task not trial, args,kwargs are of func which failed
    # exc is error object, einfo is exception object with full traceback
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            "Task FAILED task_id=%s bucket=%s key=%s exc=%s",
            task_id,
            kwargs.get("bucket"),
            kwargs.get("object_key"),
            exc,
        )
        # TODO: Update document status in Postgres to FAILED

    # first calls retry, if all exhaused, then calls on failure
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        logger.warning(
            "Task RETRY task_id=%s attempt=%d exc=%s",
            task_id,
            self.request.retries,
            exc,
        )


# crates celelry task class, with run() func running this function
@celery_app.task(
    bind=True,  # celery now attaches self in args.
    base=_BaseIngestionTask,
    name="ingestion.tasks.process_document_task",
    queue="ingestion",
    acks_late=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_document_task(
    self: Task,
    bucket: str,
    object_key: str,
    user_id: str,
    access_scope: str,
):
    get_boto3_client().download_file(
        bucket, object_key, "temp-parser.pdf", s3_download_config
    )

    # it downloads in chunks efficiently, to avoid consuming ram
    with open("temp-parser", "rb") as f:
        try:
            validate_mime_type(f.read(512), object_key)
        except ValueError:
            raise HTTPException(status_code=401, detail="only pdf files req")
        # if here dont raise then, file wont be close
