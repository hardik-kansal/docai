import asyncio
import hashlib
from .dependencies import get_DocService
from docling.datamodel.base_models import ConversionStatus
import logging
from celery import Task
from .worker import celery_app
import time

from .storage import validate_mime_type
from .dependencies import (
    get_boto3_client,
    s3_download_config,
    get_converter,
    get_chunker,
    get_vectorPool,
    get_embedModel,
)
import os
import json
import itertools
from qdrant_client.models import PointStruct
from ..config import settings
from ..dependencies import call_with_retry
from ..auth.dependencies import get_redis_pool


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
# http exceptions have no sense here these are return response for server
def process_document_task(
    self: Task,
    bucket: str,
    object_key: str,
    user_id: str,
    access_scope: str,
    filename: str,
    embedding_model: str,
    embedding_dim: int,
):
    # it downloads in chunks efficiently, to avoid consuming ram
    local_path = f"{self.request.id}.pdf"

    # This is synchronous (blocking). boto3 is sync lib
    get_boto3_client().download_file(
        bucket, object_key, local_path, Config=s3_download_config
    )

    try:
        document_hash = None
        start_time = time.perf_counter()
        with open(local_path, "rb") as f:
            validate_mime_type(f.read(2048), object_key)
            f.seek(0)
            document_hash = hashlib.sha256(f.read()).hexdigest()
        print("document hashing time")
        print((time.perf_counter() - start_time) * 1000)
        docService = get_DocService()

        # async def check_if_duplicate_document() -> bool:
        #     return await docService.check_document(user_id, document_hash)

        # is_duplicate = asyncio.get_event_loop().run_until_complete(
        #     check_if_duplicate_document()
        # )
        # if is_duplicate:
        #     return  # what if document added chunks failed
        #     # not idompotent

        result = get_converter().convert(local_path)  # 3 sec for one page
        # ram peaks here, complete file into ram, can do batch but bad results
        error = None
        if result.status == ConversionStatus.FAILURE:
            raise ValueError(f"Docling conversion failed: {result.errors}")
        elif result.status == ConversionStatus.PARTIAL_SUCCESS:
            # some text did not parsed, doesnt mean these are images, or something else
            error = json.dumps(result.errors, default=str)
            for err in result.errors:
                logger.warning(err.error_message)

        doc = result.document  # everything in ram
        chunker = get_chunker()
        chunks = chunker.chunk(doc)  # type-> iterrator[basechunk]
        # all chunks have not computed yet, this is a generator, use next(),

        async def persist_document_data():
            start_time = time.perf_counter()
            document_id = await docService.register_document(
                user_id=user_id,
                s3_key=object_key,
                filename=filename,
                content_hash=document_hash,
                docling_doc_uri="",
                embedding_model=embedding_model,
                embedding_dim=embedding_dim,
                error=error,
            )
            print("document registering time")
            print((time.perf_counter() - start_time) * 1000)

            BATCH_SIZE = 100  # keeps RAM flat

            embed_model = get_embedModel()
            vector_pool = get_vectorPool()
            enumerated_chunks = enumerate(chunks)

            for chunk_batch in itertools.batched(enumerated_chunks, BATCH_SIZE):
                db_batch = [
                    docService.create_record_row(idx, chunk, chunker, document_id)
                    for idx, chunk in chunk_batch
                ]
                start_time = time.perf_counter()
                await docService._repo.bulk_upsert_chunks(db_batch)
                print("chunk upsert time")
                print((time.perf_counter() - start_time) * 1000)
                chunk_ids = [row[0] for row in db_batch]  # uuid.UUID
                texts = [row[4] for row in db_batch]  # contextualized_text

                # v is numpy array of floats, sync cpu heavy
                start_time = time.perf_counter()
                vectors: list[list[float]] = [
                    v.tolist() for v in embed_model.embed(texts)
                ]
                print("embedding time")
                print((time.perf_counter() - start_time) * 1000)

                points = [
                    PointStruct(
                        id=str(chunk_id),
                        vector={"dense": vector},
                        payload={
                            "document_id": str(document_id),
                            "chunk_index": db_batch[i][2],
                            "text": db_batch[i][3],
                            "contextualized_text": texts[i],
                            "headings": db_batch[i][6],
                            "page_numbers": db_batch[i][7],
                            "user_id": user_id,
                        },
                    )
                    for i, (chunk_id, vector) in enumerate(zip(chunk_ids, vectors))
                ]
                start_time = time.perf_counter()
                await call_with_retry(
                    vector_pool.upsert,
                    budget_s=10,  # seconds
                    collection_name=settings().COLLECTION,
                    points=points,
                    wait=False,
                    # means for any read query doesnt wait,
                    # so now for all batches in run parallelly
                    # else would have complete index sequentially batch by batch
                )
                print("embeding index time")
                print((time.perf_counter() - start_time) * 1000)

            # All chunks embedded and indexed — mark document ready
            await docService.update_document_status(document_id, "ready")
            message = {
                "user_id": user_id,
                "document_id": str(document_id),
            }  # python dict needs to be converted to json

            # publish doesnt store in redis,
            # as soon as redis receives it, it forwards to all subscribers
            # if nobody listening, drops it silently
            await get_redis_pool().publish(
                settings().REDIS_CHANNEL_DOCS, json.dumps(message)
            )

        asyncio.get_event_loop().run_until_complete(persist_document_data())

    finally:
        logger.error("could not parsed")
        os.unlink(local_path)


"""
asyncpg.create_pool uses asyncio.
asyncio creates a internal event loop which is tied to asyncio.
every connection in that pool object, uses same event loop.

if we do asyncio.run(persist_document_data()), 
it creates a new event loop, uses pool object in that event loop.
but pool was tied to the loop it created during init,
or say in use, so we get error like
"cannot perform operation: another operation is in progress"

we can do like asyncio.run(
first init-> use pool -> close it/or just return
)

every lib which uses asyncio in bg uses same event loop,
its a rule in python else causes runtime errors or race condition.

"""
