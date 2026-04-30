"""Tests for async message bus."""
import pytest
import asyncio
from ftcoding.kernel.bus import MessageBus, Message


class TestMessageBus:
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("test.topic", handler)
        await bus.publish("test.topic", {"data": "hello"})
        await asyncio.sleep(0.01)

        assert len(received) == 1
        assert received[0].topic == "test.topic"
        assert received[0].payload == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        bus = MessageBus()
        received1 = []
        received2 = []

        bus.subscribe("test.topic", lambda m: received1.append(m))
        bus.subscribe("test.topic", lambda m: received2.append(m))

        await bus.publish("test.topic", "hello")
        await asyncio.sleep(0.01)

        assert len(received1) == 1
        assert len(received2) == 1

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = MessageBus()
        received = []

        handler = lambda m: received.append(m)
        bus.subscribe("test.topic", handler)
        bus.unsubscribe("test.topic", handler)

        await bus.publish("test.topic", "hello")
        await asyncio.sleep(0.01)

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_request_response(self):
        bus = MessageBus()

        async def handler(msg):
            return {"result": msg.payload["x"] * 2}

        bus.subscribe("math.double", handler)
        response = await bus.request("math.double", {"x": 5})

        assert response == {"result": 10}
