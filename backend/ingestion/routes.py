"""
Two endpoints:
  GET  /get-upload-url   → returns presigned PUT URL to browser
  POST /webhook/minio    → receives MinIO bucket notification, enqueues Celery task
"""

from fastapi import Body
import logging
from typing import Annotated
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Header, status

from ..config import settings
from ..models.document import (
    PresignedURLRequest,
    PresignedURLResponse,
)
from .storage import generate_presigned_put_url, _verify_minio_hmac
from .tasks import process_document_task
from ..auth.dependencies import get_current_user, User


logger = logging.getLogger(__name__)
settings = settings()

router = APIRouter(prefix="/ingestion")


@router.get("/get-upload-url")
async def get_upload_url(
    filename: str,
    content_type: str = "application/pdf",
    file_size_bytes: int = 0,
    user: User = Depends(get_current_user),
) -> PresignedURLResponse:
    request_data = PresignedURLRequest(
        filename=filename,
        content_type=content_type,
        file_size_bytes=file_size_bytes,
    )

    object_key = f"uploads/{user.user_id}/{filename}"
    # in s3 everything is stored as just key value pair, not folders but
    # s3 console ui shows folders hiearchy which is caused by "/"
    try:
        return generate_presigned_put_url(
            object_key=object_key,
            content_type=request_data.content_type,
            file_size_bytes=request_data.file_size_bytes,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="file size exceeded")


# this is addded as env while launching minio using docker
#  webhook fired by minio one user uploads to bucket
@router.post("/webhook/minio", status_code=status.HTTP_202_ACCEPTED)
async def minio_webhook(
    request: Request,
    x_minio_event: Annotated[str | None, Header()] = None,
    # in fastapi, Header() will look for request.headers
    # and try to find "x-minio-event" var name, hypen replaced
    # and assign its value to same alias
    # acc to standard, http headers are case insensitve.
    x_minio_signature: Annotated[str | None, Header()] = None,
    body_bytes: Annotated[bytes | None, Body()] = None,
    # in fastapi, body returns as a whole
    # also packets are received in stream, so Body() waits till
    # every packet is received and ordered.
) -> dict:
    try:
        _verify_minio_hmac(body_bytes, x_minio_signature)
    except ValueError:
        raise HTTPException(status_code=401)

    payload = await json.loads(body_bytes)

    # MinIO sends Records array — process each (usually 1 per webhook)
    records = payload.get("Records", [])
    queued = []

    for record in records:
        event_name: str = record.get("eventName", "")
        if "ObjectCreated" not in event_name:
            continue  # Ignore delete/copy events

        s3_info = record.get("s3", {})
        bucket = s3_info.get("bucket", {}).get("name", None)
        obj_key = s3_info.get("object", {}).get("key", None)
        obj_size = s3_info.get("object", {}).get("size", 0)
        if obj_size > settings.max_file_size_bytes:
            raise ValueError(
                f"Object {obj_key} size {obj_size} exceeds max "
                f"{settings.max_file_size_bytes}"
            )
        if bucket is None or obj_key is None:
            continue

        # this process_document_task is a func in code, but it is wrapped inside decorator
        # and celery task class is returned
        task = process_document_task.delay(
            bucket=bucket,
            object_key=obj_key,
            user_id=obj_key.split("/")[1],
            access_scope="default",
        )
        """
        celery does not excecute immediately when delay() is called, instead create this json
            {
                "task": "process_document_task",
                "args": [...],
                "kwargs": {...}
            }
        and stores it in Redis. then ask redis for any new task.

"""

        queued.append({"task_id": task.id, "key": obj_key})

    # header status code will be 202 passed, other wise minio again tries
    return {"queued": queued, "count": len(queued)}


"""

{
  "Records": [
    {
      "s3SchemaVersion": "1.0",
      "configurationId": "FastAPI-Chunk-Trigger",
      "eventTime": "2026-06-29T22:15:30.123Z",
      "eventName": "s3:ObjectCreated:Put",
      "userIdentity": {
        "principalId": "minioadmin"
      },
      "requestParameters": {
        "principalId": "minioadmin",
        "region": "us-east-1",
        "sourceIPAddress": "127.0.0.1"
      },
      "responseElements": {
        "x-amz-id-2": "dd9025bab4ad464b049177c95eb6ebf304961e",
        "x-amz-request-id": "17C0E4B07E4407B0"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "FastAPI-Chunk-Trigger",
        "bucket": {
          "name": "contracts",
          "ownerIdentity": {
            "principalId": "minioadmin"
          },
          "arn": "arn:aws:s3:::contracts"
        },
        "object": {
          "key": "user_manual.pdf",
          "size": 1048576,
          "eTag": "b10a8db164e0754105b7a99be72e3fe5",
          "contentType": "application/pdf",
          "sequencer": "17C0E4B07E4E9890"
        }
      },
      "source": {
        "host": "127.0.0.1",
        "port": "",
        "userAgent": "Mozilla/5.0..."
      }
    }
  ]
}


"""
