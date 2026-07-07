from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    stop_after_delay,
    wait_random_exponential,
    retry_if_exception_type,
)


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
    ):
        with attempt:
            return await fn(*args, **kwargs)
