"""Async message bus for inter-plugin communication."""
from __future__ import annotations
import asyncio
import uuid
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Message:
    """A message on the bus."""
    topic: str
    payload: Any
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    reply_to: str | None = None


Handler = Callable[[Message], Awaitable[Any]]


class MessageBus:
    """Async pub/sub message bus for plugin communication."""

    def __init__(self):
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._pending_responses: dict[str, asyncio.Future] = {}

    def subscribe(self, topic: str, handler: Handler) -> None:
        """Subscribe a handler to a topic."""
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        """Unsubscribe a handler from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [
                h for h in self._subscribers[topic] if h != handler
            ]

    async def publish(self, topic: str, payload: Any) -> None:
        """Publish a message to all subscribers."""
        msg = Message(topic=topic, payload=payload)
        handlers = self._subscribers.get(topic, [])

        if not handlers:
            return

        await asyncio.gather(
            *[self._invoke_handler(h, msg) for h in handlers],
            return_exceptions=True
        )

    async def request(self, topic: str, payload: Any, timeout: float = 30.0) -> Any:
        """Publish a message and wait for a response."""
        reply_topic = f"reply.{uuid.uuid4()}"
        msg = Message(
            topic=topic,
            payload=payload,
            reply_to=reply_topic
        )

        future = asyncio.get_event_loop().create_future()
        self._pending_responses[reply_topic] = future

        handlers = self._subscribers.get(topic, [])
        if not handlers:
            del self._pending_responses[reply_topic]
            raise RuntimeError(f"No handlers for topic: {topic}")

        # Use first handler for request/response
        asyncio.create_task(self._invoke_handler_with_reply(handlers[0], msg))

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            del self._pending_responses[reply_topic]
            raise TimeoutError(f"Request to {topic} timed out")

    async def _invoke_handler(self, handler: Handler, msg: Message) -> None:
        """Invoke a handler, catching exceptions."""
        try:
            await handler(msg)
        except Exception as e:
            # Log but don't crash the bus
            print(f"Handler error on {msg.topic}: {e}")

    async def _invoke_handler_with_reply(self, handler: Handler, msg: Message) -> None:
        """Invoke a handler and send reply."""
        try:
            result = await handler(msg)
            if msg.reply_to and msg.reply_to in self._pending_responses:
                future = self._pending_responses.pop(msg.reply_to)
                if not future.done():
                    future.set_result(result)
        except Exception as e:
            if msg.reply_to and msg.reply_to in self._pending_responses:
                future = self._pending_responses.pop(msg.reply_to)
                if not future.done():
                    future.set_exception(e)
