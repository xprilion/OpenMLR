"""HTTP utilities with exponential backoff and retry logic for external APIs."""

import asyncio
import logging
import random
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import httpx

log = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimitError(Exception):
    """Raised when rate limit is hit."""

    def __init__(self, retry_after: float | None = None):
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit hit, retry after {retry_after}s" if retry_after else "Rate limit hit"
        )


class APIError(Exception):
    """Raised for non-retryable API errors."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API error {status_code}: {message}")


async def fetch_with_retry(
    url: str,
    *,
    method: str = "GET",
    params: dict | None = None,
    headers: dict | None = None,
    json: dict | None = None,
    timeout: float = 30,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retry_statuses: set[int] | None = None,
) -> httpx.Response:
    """
    Make an HTTP request with exponential backoff retry.

    Args:
        url: Request URL
        method: HTTP method (GET, POST, etc.)
        params: Query parameters
        headers: Request headers
        json: JSON body for POST/PUT
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        base_delay: Base delay for exponential backoff
        max_delay: Maximum delay between retries
        retry_statuses: HTTP status codes to retry (default: 429, 500, 502, 503, 504)

    Returns:
        httpx.Response on success

    Raises:
        RateLimitError: If rate limit persists after retries
        APIError: For non-retryable errors
        httpx.TimeoutException: If request times out after retries
    """
    if retry_statuses is None:
        retry_statuses = {429, 500, 502, 503, 504}

    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    json=json,
                    timeout=timeout,
                )

                # Success
                if response.status_code < 400:
                    return response

                # Rate limit - check for Retry-After header
                if response.status_code == 429:
                    retry_after = _parse_retry_after(response)
                    if attempt < max_retries:
                        delay = (
                            retry_after
                            if retry_after
                            else _calculate_delay(attempt, base_delay, max_delay)
                        )
                        log.warning(
                            f"Rate limit hit for {url}, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    raise RateLimitError(retry_after)

                # Retryable server error
                if response.status_code in retry_statuses:
                    if attempt < max_retries:
                        delay = _calculate_delay(attempt, base_delay, max_delay)
                        log.warning(
                            f"Server error {response.status_code} for {url}, retrying in {delay:.1f}s"
                        )
                        await asyncio.sleep(delay)
                        continue

                # Non-retryable error - return response for caller to handle
                return response

        except httpx.TimeoutException as e:
            last_exception = e
            if attempt < max_retries:
                delay = _calculate_delay(attempt, base_delay, max_delay)
                log.warning(f"Timeout for {url}, retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
                continue
            raise

        except httpx.RequestError as e:
            last_exception = e
            if attempt < max_retries:
                delay = _calculate_delay(attempt, base_delay, max_delay)
                log.warning(f"Request error for {url}: {e}, retrying in {delay:.1f}s")
                await asyncio.sleep(delay)
                continue
            raise

    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise APIError(500, "Max retries exceeded")


def _calculate_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Calculate exponential backoff delay with jitter."""
    delay = min(base_delay * (2**attempt), max_delay)
    # Add jitter (±25%)
    jitter = delay * 0.25 * (random.random() * 2 - 1)
    return max(0.1, delay + jitter)


def _parse_retry_after(response: httpx.Response) -> float | None:
    """Parse Retry-After header value."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    return None


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """
    Decorator for adding retry logic to async functions that make HTTP calls.

    The decorated function should raise RateLimitError or APIError for retryable errors.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except RateLimitError as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = (
                            e.retry_after
                            if e.retry_after
                            else _calculate_delay(attempt, base_delay, max_delay)
                        )
                        log.warning(f"Rate limit in {func.__name__}, retrying in {delay:.1f}s")
                        await asyncio.sleep(delay)
                        continue
                    raise
                except httpx.TimeoutException as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = _calculate_delay(attempt, base_delay, max_delay)
                        log.warning(f"Timeout in {func.__name__}, retrying in {delay:.1f}s")
                        await asyncio.sleep(delay)
                        continue
                    raise

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator
