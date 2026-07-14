from celery import Celery
from ..config import settings
from celery.signals import worker_process_init
import boto3
from botocore.config import Config
from .dependencies import (
    set_boto3_client,
    set_converter,
    set_chunker,
    init_pg_connection,
    set_vectorPool,
    set_embedModel,
)
import asyncpg
from ..auth.dependencies import set_asyncpg_pool, set_redis_pool
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureOptions,
    AcceleratorOptions,
    AcceleratorDevice,
)
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
)
from docling_core.transforms.serializer.markdown import (
    MarkdownParams,
    MarkdownTableSerializer,
)
from transformers import AutoTokenizer
import asyncio
from qdrant_client import AsyncQdrantClient, models
from fastembed import TextEmbedding
import redis.asyncio as redis

celery_app = Celery(
    "project1_celery",  # just application name
    broker=settings().REDIS_URL,  # delay() stores here
    backend=settings().REDIS_URL,  # task result is stored here, return value of fucntion called
    include=[
        "backend.ingestion.tasks"
    ],  # file where tasks are there, need before runtime
)

# celery does not use threads inside, each worker assigns one task, with just master thread
celery_app.conf.update(
    # Serialization — JSON only, never pickle which is defualt (security issue)
    # pickle.loads/dumps -> convert anything into bytes, so might also convert malacious code.
    task_serializer="json",  # when using delay() to store task in redis
    result_serializer="json",  # return value of func when run by worker
    accept_content=[
        "json"
    ],  # when worker picks up task from redis to run, accepts json
    # suppose one worker process crashes, could not even tell redis about this through ack_late
    # redis will handover this task if it doesnt listen ack_late form that worker process in this time.
    broker_transport_options={"visibility_timeout": 3600},  # 1hr
    # must be large enough than task processing time,
    #  else two workers would be doing duplicate tasks
    # this make sure when task completed only then worker send ack_sucess
    task_acks_late=True,
    task_reject_on_worker_lost=True,  # if recived ack_late, handover to another by requeue
    # One task per worker process,
    # else celery might assign many to one worker, while others are still idle
    worker_prefetch_multiplier=1,
    # this task will go to ingestion queue.
    task_routes={
        "ingestion.tasks.process_document_task": {"queue": "ingestion"},
    },
    # Retry policy applied to all tasks, else use default
    task_default_retry_delay=30,  # seconds
    task_max_retries=3,
)


# Idempotent delivery: means every task runs at-least-once with ack-on-success
# celery gurantees with these config that a task will not be silently lost
# and it will retry it
# but what if task completely sucessfully then some problem occurs
# and redis handover this task to another worker, task will run twice.
# thats why our task code neeeds to be idompotent,
# means running it multiple times would give same final state, as if run only once.
# say if task updates a balance, then balance might be updated twice.


"""

first Celery Master process starts up, it runs code that tell os
-> Hey kernel, take an exact snapshot of me right now, 
clone it, and paste it into a brand new, independent memory space using os fork()
-> The OS gives them their own unique PIDs and isolated memory blocks.
-> after that detaches this pid from master, 
-> and runs each child as a complete unrealted seperate process not threads


Now Each worker process is an independent Python process with:

its own memory
its own GIL
but share same filesystem -> not idompotent
"""


# runs only once, before child process accepts its first task, boto3 is sync lib
@worker_process_init.connect
def init_worker_s3(**kwargs):
    client = boto3.client(
        "s3",
        endpoint_url=settings().minio_endpoint,
        aws_access_key_id=settings().minio_access_key,
        aws_secret_access_key=settings().minio_secret_key,
        region_name=settings().minio_region,
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    )
    set_boto3_client(client)


# Create one event loop for this worker process, so now
# one worker,sep process completely,
#  handles one task,
#  one main thread no child threads (os dont create threads by itself, lib do)
# since cerlry is sync,
# with one event loop running


async def init_clients():
    pool = await asyncpg.create_pool(
        dsn=settings().DB_URL, min_size=2, max_size=10, init=init_pg_connection
    )
    set_asyncpg_pool(pool)

    vectorPool = AsyncQdrantClient(
        url=settings().QDRANT_URL, api_key=settings().QDRANT_API_KEY
    )
    name = settings().COLLECTION
    if not await vectorPool.collection_exists(name):
        await vectorPool.create_collection(
            collection_name=name,
            vectors_config={
                "dense": models.VectorParams(
                    size=settings().EMBED_MODEL_DIM, distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(modifier=models.Modifier.IDF)
            },
        )
        # value,keys are str matched
        for field, schema in [
            ("user_id", models.PayloadSchemaType.KEYWORD),
            ("document_id", models.PayloadSchemaType.KEYWORD),
        ]:
            await vectorPool.create_payload_index(
                name, field_name=field, field_schema=schema
            )
    set_vectorPool(vectorPool)

    embedModel = TextEmbedding(model_name=settings().EMBED_MODEL_ID)
    set_embedModel(embedModel)

    _redis_pool = redis.Redis.from_url(
        settings().REDIS_URL,
        decode_responses=True,
        max_connections=20,
    )
    await _redis_pool.ping()
    set_redis_pool(_redis_pool)


@worker_process_init.connect
def init_worker_clients(**kwargs):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_clients())


@worker_process_init.connect
def preload_converter(**kwargs):
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options = TableStructureOptions(
        do_cell_matching=True
    )
    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=8, device=AcceleratorDevice.AUTO
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    set_converter(converter)


# derfault serializer do "row,col=value"
# this fails if req say row,(col,col,col)=value"abs
# thats why this req, it preserves grid, but uses more tokens
class MarkdownTableSerializerProvider(ChunkingSerializerProvider):
    def get_serializer(self, doc):
        return ChunkingDocSerializer(
            doc=doc,
            table_serializer=MarkdownTableSerializer(),
            params=MarkdownParams(compact_tables=True),
            # very imp, compact tables removes padding, quite uncessary
            # default is actually false.
        )


@worker_process_init.connect
def preload_chunker(**kwargs):
    chunker = HybridChunker(
        tokenizer=HuggingFaceTokenizer(
            tokenizer=AutoTokenizer.from_pretrained(settings().EMBED_MODEL_ID),
            max_tokens=settings().MAX_TOKENS,
        ),
        merge_peers=True,  # merges undersized sibling chunks
        repeat_table_header=True,  # each split chunk gets the header row re-attached
        serializer_provider=MarkdownTableSerializerProvider(),
    )
    set_chunker(chunker)


"""

do_ocr = False → OCR never runs;Correct setting for a pure-text PDF, and the fastest.

do_ocr = True with the default force_full_page_ocr = False 
-> Docling runs in what the docs call "hybrid detection":
-> it prefers the existing text layer and only OCRs regions that don't have one 
-> (e.g. a scanned image embedded on an otherwise digital page). 
-> On a pure-text PDF there's nothing for OCR to fill in, so the output shouldn't change 
—> but the OCR engine still gets loaded and run as a pass over every page

do_ocr = True + force_full_page_ocr = True 
-> This forces OCR over every page regardless of whether a text layer exists
-> and it will replace your clean digital text with re-OCR'd text. 
-> Never use this on text only PDFs -> confirmed bugs

"""


"""

why celery?
oldest, most widely known, dominates job postings but it's sync-first, can do async work too.

arq: asyncio-native, very less maintainace

Taskiq: "Celery for async," actively maintained, multiple broker support (Redis/RabbitMQ/NATS/Kafka).Downside: smaller community, not a recognized keyword in job postings, less battle-tested at scale than Celery.

SAQ: async, actively maintained, ships a built-in web UI for watching jobs Downside: smallest community of the four, only redis support


Taskiq
Suppose one worker process is there (each worker/one cpu).It has one asyncio event loop.

Task A await 5s
Task B await 5s
when task a waits, task b spins on core.


Celery
one worker process executes one task.
Even though taska is taking 5 seconds, that process is still considered busy with Task A. It will not start Task B in that same process.
Concurrency comes from more processes, not from multiplexing many coroutines inside one process.

but if task is more 
pdf = parse_pdf_locally()      # CPU-heavy
embeddings = local_model(pdf)  # CPU/GPU-heavy
taskiq gains nothing

in this case, taskiq can work faster.

Download PDF      200 ms 
Parse PDF         800 ms (CPU) if gpu then taskiq more faster
Chunk             100 ms (CPU)
OpenAI            4 s  
Qdrant            100 ms 
Postgres          50 ms

But celery is more trusted for every other case with complex workflows handling.

"""
