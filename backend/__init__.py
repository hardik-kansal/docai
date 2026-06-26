# since auth files uses .. to get files form backend its needs to be package


"""
logging practises?
> use info for every route endpoint, at starting, at end of func using middleware
> use info for lifespan, major milestone with try/except
> use critical in except for major milestone
> use warning in every except if handled via fallback func
> use error in every except if raised
> use try/except only if
    - there is fallback func to call
    - needs to raise custom error
> use debug only in internal debugging where ever you want off in prod
> any unhandled exception anywhere, reaches Starlette's built-in ServerErrorMiddleware
> which returns http response 500 Internal Server Error instead of crashing the server
> every except block must raise some error, if there is no fallback to do
> else it would corrupt the system
> dont use f based formatting since string is created first then logging level is checked.
> also dont use %s based, since then regex based checking is used.
> use extra={} in logging, now can search easily, index too.
> in logging, omit nulls to log.
> always use strutured json logging

401 Unauthorized -> User is not authenticated
403 Forbidden -> User is authenticated but lacks permission.
409 Conflict -> Request is valid, but conflicts with current server state.
400 Bad Request -> Request is malformed or invalid.
422 Unprocessable Entity -> pydantic automatically returns this when request validation fails.

> All these httpException are valid response to client,
so not handled by ServerErrorMiddleware
except these, all remaining errors are mapped to 500 Internal Server Error
> http exceptions are not logged in Routemiddleware.
> all remaining errors are logged with full trace,
so not req to do exc_info=True anywhere except for HTTPException
> if its necessary only then log HTTPException, since these are generally
invalid credentails scopes business logic based, not server infra problem.
> for all server, infra except during startup and shutdown, Routemiddleware handles it
and ServerErrorMiddleware returns 500 response

> Main goal is if some business logic fails, raise custom exception
> catch this exception in route and map it to http response.

> catch errors only in routes bz there might be some cleanup do it
> if though catched inside, and raise http inside-> cleanup might miss
> dont use var used in try inside except since they might not be assigned properly.

How to handle logs?

Observability
├── Logs with error stack trace
├── Metrics -> Numeric measurements over time. -> promethius
                Requests/sec = 1200
                CPU = 72%
                Memory = 8GB
                Error Rate = 0.5%
└── Traces -> Track a request through many services.
                POST /login
                │
                ├── JWT Verify        4ms
                ├── Redis            10ms
                ├── PostgreSQL       80ms
                └── Response          5ms
1. mvp -> onto terminal but lost if server crashes

2. startups -> app.log file, but if scale to many servers, ssh into each to find bug

3. industry->
Log Shipper (like FluentBit, Logstash, or Promtail) sits on the machine.
-> kafka(high speed buffer)
-> central database like Elasticsearch, OpenSearch, Grafana Loki, or Datadog
-> visualizaion tools
-> some tool combines all three observibility, work like all layers eg datadog

4. using in memory async buffer and a single bg thread can flush it to db in batches
-> bg thread releases gil instantly since its os job now for network or i/o
-> in memory buffer can grow competes with app memory, use bounded queue
-> use with app lifespan, so while shuting down app flushes remaining logs to db
-> in case of crash, logs are lost, in case of queue fills, raises error
-> catch error and either drop low prirorty logs, increase size.

Industry method adds very little latency compare to in memory roughly 20us.
as writing to terminal is os buffered pipe job, and adds very less latency.
also if i have to logs db, needs to change app code.
if app crashes, logs are lost in in process queue.






AUTH/

cookies.py
-> is imported in 4 files better to create a seperate file for this to avoid
circular dependency

repository.py
> for each table, class to interact and row class
> handles all sql queries part, insert, exits, create into table

tokens.py
> kind of helper, to decode encode tokens,
> TokenPayload defined here, though decode,encode cookies is handled interanlly
> but get_current_user needs to return something, why not make it a object

token_store.py
> redis class, diectly storing retreiving as json
> only those which are send to user and recieved from user needs seperate object
> so that we can inherit pydanctic base model

routes.py
> handles all auth routes, login/logout/signup/
> LoginRequest defined here

services.py (routes -> servies -> repository) this pattern is used for db
> servies raises app error, routes catches it, raise http instead
> this is done to traceback actual error in production
> this file handles combination of direct sql queries need,
> sql must not be used directly in routes endpoint function

dependencies.py
> all those functions which would be called via Depends() in route endpoint
> db, redis connection pool variables, setter, getter functions since
> since all these are called via lifespan dependency of fastapi


DB/
migrations/



Scenario 1: Side-by-Side Execution
@app.get("/items")
async def get_items():
    await db.fetch() # The server pauses here and switches to Request 2!

Scenario 2: Hidden Side-by-Side Execution (Standard def)
def get_items():
    time.sleep(5) # Blocks this thread, but other threads stay open!
FastAPI automatically offloads Request 1 to a separate Background Thread Pool.
But in case of traffic, threads would get increase and decrease performance.

Scenario 3: One-After-Another Execution
@app.get("/items")
async def get_items():
    time.sleep(5) # This freezes the entire event loop!


"""
