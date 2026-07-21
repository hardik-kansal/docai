import asyncio
from ..models.schemas import PLANS, PlanType
import logging
import json
from fastapi import APIRouter, Depends, Request, Header, HTTPException
import secrets
from urllib.parse import unquote_plus
from ..config import settings
from ..models.document import PresignedURLResponse, DocumentResponse

from typing import Annotated
from .storage import generate_presigned_post_url, generate_presigned_get_url
from .tasks import process_document_task, delete_document_task
from ..auth.dependencies import (
    get_current_user,
    User,
    get_auth_service,
    AuthService,
    get_redis_pool,
)

from .dependencies import get_DocService, get_boto3_client
from .services import DocService
import uuid
from sse_starlette.sse import EventSourceResponse
from ..dependencies import get_connections_event

logger = logging.getLogger(__name__)
settings = settings()

router = APIRouter(prefix="/api/v1/ingestion")


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


# Returns 202 Accepted — cleanup is in flight, not yet complete.
@router.delete("/documents/{document_id}", status_code=202)
async def delete_document(
    document_id: str,
    user: Annotated[User, Depends(get_current_user)],
    doc_service: Annotated[DocService, Depends(get_DocService)],
    authService: Annotated[AuthService, Depends(get_auth_service)],
):
    result = await doc_service.get_s3_key(document_id, user.user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="document not found")

    s3_key = result

    try:
        head = get_boto3_client().head_object(Bucket=settings.minio_bucket, Key=s3_key)
        file_size_bytes = head.get("ContentLength", 0)
    except Exception:
        logger.warning(
            "head_object failed for key=%s, skipping storage decrement", s3_key
        )
        file_size_bytes = 0

    if file_size_bytes > 0:
        updated_user = await authService.update_storage(user.user_id, -file_size_bytes)
        if updated_user:
            storage_message = {
                "user_id": str(updated_user.user_id),
                "storage_used_bytes": updated_user.storage_used_bytes,
                "type": "storage_update",
            }
            await get_redis_pool().publish(
                settings.REDIS_CHANNEL_DOCS, json.dumps(storage_message)
            )

    delete_document_task.delay(
        doc_id=document_id,
        s3_bucket=settings.minio_bucket,
        s3_key=s3_key,
    )

    return {"detail": "deletion in progress", "document_id": document_id}


@router.get("/documents/{document_id}/view-url")
async def get_view_url(
    document_id: str,
    user: Annotated[User, Depends(get_current_user)],
    doc_service: Annotated[DocService, Depends(get_DocService)],
):
    """Return a 15-minute presigned GET URL for the PDF.
    Ownership enforced in the DB query — wrong user gets 404, not 403,
    to avoid leaking whether a document_id exists at all.
    """
    from fastapi import HTTPException

    s3_key = await doc_service.get_s3_key(document_id, user.user_id)
    if s3_key is None:
        raise HTTPException(status_code=404, detail="document not found")
    url = generate_presigned_get_url(s3_key)
    return {"view_url": url, "expires_in": 900}


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
    return generate_presigned_post_url(
        object_key=object_key,
        max_bytes=PLANS[PlanType(plan_type)].max_storage_bytes - storage_used_bytes,
    )


# fastapi forwards header, and body to depends
async def verify_webhook(authorization: str = Header(None)):
    expected = settings.MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_FASTAPI
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, detail="Missing or invalid Authorization header"
        )
    token = authorization.split(" ")[1]
    print(token)
    if not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Invalid token")


# this is addded as env while launching minio using docker
#  webhook fired by minio one user uploads to bucket
# use eventBridge in production, and password checking if its actually aws
@router.post("/webhook/minio")
async def minio_webhook(
    request: Request,
    authService: Annotated[AuthService, Depends(get_auth_service)],
    _=Depends(verify_webhook),
):
    print(request.headers)
    body_bytes: bytes = await request.body()
    payload = json.loads(body_bytes)

    # MinIO sends Records array — process each (usually 1 per webhook)
    records = payload.get("Records", [])

    # AWS EventBridge format support
    if settings.is_prod:
        if "detail-type" in payload and payload.get("source") == "aws.s3":
            bucket_name = payload.get("detail", {}).get("bucket", {}).get("name")
            object_key = payload.get("detail", {}).get("object", {}).get("key")
            object_size = payload.get("detail", {}).get("object", {}).get("size", 0)

            records = [
                {
                    "eventName": "ObjectCreated:Put",
                    "s3": {
                        "bucket": {"name": bucket_name},
                        "object": {"key": object_key, "size": object_size},
                    },
                }
            ]
    for record in records:
        event_name: str = record.get("eventName", "")
        if "ObjectCreated" not in event_name:
            continue  # Ignore delete/copy events

        s3_info = record.get("s3", {})
        bucket = s3_info.get("bucket", {}).get("name", None)
        obj_key = unquote_plus(s3_info.get("object", {}).get("key", None))
        # uploads%2Fuser_id%2Fuuid%2Ffilename -> unquote url decode the string
        # converts + to spaces

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
        user_id_str = obj_key.split("/")[1]
        updated_user = await authService.update_storage(user_id_str, obj_size)
        if updated_user:
            storage_message = {
                "user_id": str(updated_user.user_id),
                "storage_used_bytes": updated_user.storage_used_bytes,
                "type": "storage_update",
            }
            await get_redis_pool().publish(
                settings.REDIS_CHANNEL_DOCS, json.dumps(storage_message)
            )

        process_document_task.delay(
            bucket=bucket,
            object_key=obj_key,
            user_id=user_id_str,
            access_scope="default",
            filename=obj_key.split("/")[3],
            embedding_model=settings.EMBED_MODEL_ID,
            embedding_dim=settings.EMBED_MODEL_DIM,
        )
        message = {
            "user_id": user_id_str,
            "object_key": obj_key,
            "status": "processing",
        }
        await get_redis_pool().publish(settings.REDIS_CHANNEL_DOCS, json.dumps(message))


# expected to call before get upload url by frontend
# then it would run until tab is closed, or refreshed
# navigating to another tab doesnt mean connection is break
@router.get("/check-doc-status")
async def check_status(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    active_connections: Annotated[
        dict[str, set[asyncio.Queue]], Depends(get_connections_event)
    ],
):
    client_queue = asyncio.Queue()
    active_connections[user.user_id].add(client_queue)
    # this expects user_id to exist by default
    # but since we have set to defualtdict, it creates empty set()
    # then adds client_queue to it.

    async def event_generator():
        try:
            while True:
                try:
                    # wait_for raises TimeoutError if no message arrives in time
                    # so we can check disconnect without waiting forever on .get()
                    event = await asyncio.wait_for(client_queue.get(), timeout=60)
                    logger.info(f"SSE sending event: {json.dumps(event)}")
                    yield {"data": json.dumps(event)}
                except asyncio.TimeoutError:
                    # no message yet — check if client has gone away
                    if await request.is_disconnected():
                        break
                        # user is gone, so browser wont try to connect

        except asyncio.CancelledError:
            print("sse stream for doc status ended")
            pass
        finally:
            active_connections[user.user_id].discard(client_queue)
            if not active_connections[user.user_id]:
                del active_connections[user.user_id]

    return EventSourceResponse(
        event_generator(),
        ping=settings.PING_INTERVAL,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# this sends 200 ok immediately
# event source causes browser to reconnect, even if we raise error
# only acc to standard, only HTTP 204 No content status code tells browser
# to stop it legally,but we coulnt send after this return is called

"""
celery does not excecute immediately when delay() is called, 
instead creates this json
    {
        "task": "process_document_task",
        "args": [...],
        "kwargs": {...}
    }
and stores it in Redis. then ask redis for any new task.

"""


"""

header send by s3 using webhook
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
