from ..models.schemas import PLANS, PlanType
import logging
import json
from fastapi import APIRouter, Depends, Request
from urllib.parse import unquote
from ..config import settings
from ..models.document import PresignedURLResponse, DocumentResponse

from typing import Annotated
from .storage import generate_presigned_put_url
from .tasks import process_document_task
from ..auth.dependencies import get_current_user, User, get_auth_service, AuthService
from .dependencies import get_DocService
from .services import DocService
import uuid


logger = logging.getLogger(__name__)
settings = settings()

router = APIRouter(prefix="/ingestion")


@router.get("/documents")
async def list_documents(
    user: Annotated[User, Depends(get_current_user)],
    doc_service: Annotated[DocService, Depends(get_DocService)],
) -> list[DocumentResponse]:
    rows = await doc_service.list_documents(user.user_id)
    return [
        DocumentResponse(
            id=str(row.id),
            filename=row.filename,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
            s3_key=row.s3_key,
            error=row.error,
        )
        for row in rows
    ]


@router.get("/get-upload-url")
async def get_upload_url(
    filename: str,
    user: Annotated[User, Depends(get_current_user)],
    authService: Annotated[AuthService, Depends(get_auth_service)],
) -> PresignedURLResponse:
    object_key = f"uploads/{user.user_id}/{uuid.uuid4()}/{filename}"
    # in s3 everything is stored as just key value pair, not folders but
    # s3 console ui shows folders hiearchy which is caused by "/"
    userRow = await authService.get_by_user_id(user.user_id)
    plan_type = userRow.plan_type
    storage_used_bytes = userRow.storage_used_bytes
    return generate_presigned_put_url(
        object_key=object_key,
        max_bytes=PLANS[PlanType(plan_type)].max_storage_bytes - storage_used_bytes,
    )


# this is addded as env while launching minio using docker
#  webhook fired by minio one user uploads to bucket
@router.post("/webhook/minio")
async def minio_webhook(
    request: Request,
    authService: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    body_bytes: bytes = await request.body()
    payload = json.loads(body_bytes)

    # MinIO sends Records array — process each (usually 1 per webhook)
    records = payload.get("Records", [])
    queued = []

    for record in records:
        event_name: str = record.get("eventName", "")
        if "ObjectCreated" not in event_name:
            continue  # Ignore delete/copy events

        s3_info = record.get("s3", {})
        bucket = s3_info.get("bucket", {}).get("name", None)
        obj_key = unquote(s3_info.get("object", {}).get("key", None))
        # uploads%2Fuser_id%2Fuuid%2Ffilename -> unquote url decode the string

        obj_size = s3_info.get("object", {}).get("size", 0)
        # if obj_size > settings.max_file_size_bytes:
        #     raise ValueError(
        #         f"Object {obj_key} size {obj_size} exceeds max "
        #         f"{settings.max_file_size_bytes}"
        #     )
        if bucket is None or obj_key is None:
            continue

        # this process_document_task is a func in code, but it is wrapped inside decorator
        # and celery task class is returned
        await authService.update_storage(obj_key.split("/")[1], obj_size)
        task = process_document_task.delay(
            bucket=bucket,
            object_key=obj_key,
            user_id=obj_key.split("/")[1],
            access_scope="default",
            filename=obj_key.split("/")[3],
            embedding_model=settings.EMBED_MODEL_ID,
            embedding_dim=settings.EMBED_MODEL_DIM,
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

header ssend by s3 using webhook
{
 'host': 'host.docker.internal:8000',
 'user-agent': 'Go-http-client/1.1', 
 'content-length': '1109', 
 'content-type': 'application/json'
 }
records in body
"[
{'eventVersion': '2.0', 
'eventSource': 'minio:s3',
'awsRegion': '', 
'eventTime': '2026-07-01T14:24:05.177Z', 
'eventName': 's3:ObjectCreated:Post', 
'userIdentity': {'principalId': ''}, 
'requestParameters': {
                      'principalId': '', 
                      'region': '', 
                      'sourceIPAddress': '172.18.0.1'
                      }, 
'responseElements': {
                      'x-amz-id-2': 'dd9025bab4ad464b049177c95eb6ebf374d3b3fd1af9251148b658df7ac2e3e8', 
                      'x-amz-request-id': '18BE3083CFADCFB5', 
                      'x-minio-deployment-id': '6341d596-30ae-4137-8ea8-4d6888080882', 
                      'x-minio-origin-endpoint': 'http://172.18.0.2:9000'
                      }, 
's3': {
    's3SchemaVersion': '1.0', 
    'configurationId': 'Config', 
    'bucket': {
        'name': 'contracts', 
        'ownerIdentity': {'principalId': ''}, 
        'arn': 'arn:aws:s3:::contracts'
    }, 
    'object': {
        'key': 'uploads%2Fab0b00856e464dd1965bea5ffd3aaaf5%2F207c1be2-e9b2-4a93-9850-7ea7c2be5261%2Fhardik', 
        'size': 1036345, 
        'eTag': '43224ef3294cfb4f1e8494498998e9b2', 
        'contentType': 'application/pdf', 
        'userMetadata': {
            'content-type': 'application/pdf'
        }, 
        'sequencer': '18BE3083D0108A53'
    }
}, 
'source': {
    'host': '172.18.0.1', 
    'port': '', 
    'userAgent': 'python-requests/2.34.2'
}




"""
