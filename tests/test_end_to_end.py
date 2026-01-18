import os
import time
import asyncio

import pytest
import httpx


pytestmark = pytest.mark.asyncio


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
RUN_INTEGRATION = os.getenv("RUN_INTEGRATION_TESTS", "0") == "1"


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Set RUN_INTEGRATION_TESTS=1 to run integration tests")
async def test_event_pipeline_end_to_end():
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0) as client:
        # Wait for service
        deadline = time.time() + 30
        while True:
            try:
                r = await client.get("/health")
                if r.status_code == 200:
                    break
            except Exception:
                pass

            if time.time() > deadline:
                raise AssertionError("API did not become healthy in time")
            await asyncio.sleep(1)

        # Produce event
        body = {"event_type": "demo.test", "payload": {"hello": "world"}}
        r = await client.post("/events", json=body)
        assert r.status_code == 202

        # Poll Postgres-backed endpoint until consumer persists it
        deadline = time.time() + 30
        while True:
            r = await client.get("/events")
            assert r.status_code == 200
            events = r.json()
            if any(e["event_type"] == "demo.test" and e["payload"].get("hello") == "world" for e in events):
                return

            if time.time() > deadline:
                raise AssertionError("Event was not persisted within expected time")
            await asyncio.sleep(1)
