from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    stop_after_delay,
    wait_random_exponential,
    retry_if_exception_type,
)
from aiobreaker import CircuitBreaker
from datetime import timedelta


async def call_with_retry(
    fn,
    *args,
    budget_s: float,
    max_attempts: int = 3,
    retryable=(TimeoutError, ConnectionError),
    **kwargs,
):
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts)
        | stop_after_delay(budget_s),  # whichever hits first
        wait=wait_random_exponential(
            multiplier=0.2, max=2
        ),  # jittered — avoids synchronized retry storms
        retry=retry_if_exception_type(retryable),
        reraise=True,
        # else would throw tencaity retry errror rather than application error
    ):
        with attempt:
            return await fn(*args, **kwargs)


circuit_breaker: CircuitBreaker = CircuitBreaker(
    fail_max=5,
    timeout_duration=timedelta(seconds=30),
)


def get_circuit_breaker() -> CircuitBreaker:
    return circuit_breaker


"""
there are three realibility considerations - 

1. retry with exponential backoff -> 
only for transient network failures, 
probably goona succed in next retry, just packet miss kinda
use only when call is itempotent, else retry calls diff results

2. timeout ->
use for all external calls always
req is send to external api, and we awaits for result, till timeout

3. Circuit breaker -> 
some req are send, waits for result, 
result is either no exception, exception, 
or our logic to declare exception via timeout 
then opens cb, now every next req fails immediately instead of waiting
close after a time, checks next req if fail again, 
closes it for same time again

three lib for cb -> (very basic not true compeltely)
pybreaker for sync
aiobreaker for async
purgatory (state stored, so that multiple workers can know total failures yet)


cb -> retry logic with expo backoff -> timeout -> external call
cb would consider failure only when all retires fails for a req
when this happens for some given no of req, opens it.
if retry logic uppermost -> very problematic

some external calls apply some of these layers by defualt
either change their default to 0, or use their else high waiting time to user.

all clients used in project have timeout logic, no circuit breaker
pg,qdrant have no retry logic (expected)
gemini,boto3,redis have it 

"""
