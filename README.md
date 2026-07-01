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


Here is what ChatGPT sees for each message, in order:

System Instructions. Rules that define how ChatGPT should behave
Developer Instructions. Additional configuration from the app or interface
Session Metadata. Temporary details about your current environment

Here is what a session metadata block might look like:

Subscription: ChatGPT Plus
Device: Desktop browser
Browser: Safari on macOS
Location: United Kingdom
Local time: 14:30
Account age: 52 weeks
Activity: Used 6 of the last 7 days
Average messages per conversation: 12
Model usage: 60% GPT-4o, 30% GPT-4o-mini, 10% o14

User Memory->Permanent facts stored about you
Recent Conversations Summary->brief notes from your past chats, only questions summary
Current Session Messages-> Everything said in this conversation so far, this is the 
                          first thing that deletes in case of low context window


uploading document
pdfparser->cleaning/normalization->pii redaction->chunking->embed->store in vector


user query
cleaning -> query rewriter ->embed ->search in vector-> retirval->attach context->prompt buildr->llm->guardrails->reponsee with citations
