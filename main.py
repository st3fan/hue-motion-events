# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/


import asyncio
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from typing import Generator, List
import urllib.parse

import iso8601
from aiohttp import ClientSession
from aiohttp_sse_client.client import EventSource, MessageEvent
import asyncpg


logger = logging.getLogger("hue-motion-events")


def _event_stream_url(bridge_address: str) -> str:
    return f"https://{bridge_address}/eventstream/clip/v2"


def _redact_dsn(dsn: str) -> str:
    u = urllib.parse.urlparse(dsn)
    if u.password:
        dsn = dsn.replace(u.password, "REDACTED")
    return dsn


@dataclass
class MotionEvent:
    creationtime: datetime
    device_id: str
    motion: bool


def _parse_motion_events(message_event_data: dict) -> Generator[MotionEvent, None, None]:
    for events in message_event_data:
        if events.get("type") == "update":
            for event in events.get("data", []):
                if event.get("type") == "motion":
                    yield MotionEvent(iso8601.parse_date(events.get("creationtime")), event.get("id"), event.get("motion").get("motion"))


async def process_message_event(message_event: MessageEvent, conn: asyncpg.connection.Connection):
    message_event_data = json.loads(message_event.data)
    for event in _parse_motion_events(message_event_data):
        await conn.execute("insert into motion_events (ts, device_id, motion) values ($1, $2, $3)", event.creationtime, event.device_id, event.motion)


async def receive_events(application_key: str, event_stream_url: str, conn: asyncpg.connection.Connection):
    headers = {
        "hue-application-key": application_key,
        "Accept": "text/event-stream"
    }

    async with ClientSession(headers=headers, raise_for_status=True) as session:
        async with EventSource(event_stream_url, session=session, verify_ssl=False) as events:
            try:
                async for event in events:
                    try:
                        await process_message_event(event, conn)
                    except Exception as e:
                        logger.error(f"Error while processing event", e)
            except ConnectionError as e:
                logger.error(f"Error connecting to {event_stream_url}", e)
            except Exception as e:
                logger.error("Error handling events", e)


async def main():
    application_key = os.getenv("HUE_APPLICATION_KEY")
    if not application_key:
        raise SystemExit("cannot run without HUE_APPLICATION_KEY")

    bridge_address = os.getenv("HUE_BRIDGE_ADDRESS")
    if not bridge_address:
        raise SystemExit("cannot run without HUE_BRIDGE_ADDRESS")

    postgres_dsn = os.getenv("POSTGRES_DSN")
    if not postgres_dsn:
        raise SystemExit("cannot run without POSTGRES_DSN")

    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(level=log_level)

    event_stream_url = _event_stream_url(bridge_address)

    logging.info(f"Connecting to database <{_redact_dsn(postgres_dsn)}>")
    conn = await asyncpg.connect(postgres_dsn)

    logging.info(f"Connecting to event source <{event_stream_url}>")
    await receive_events(application_key, event_stream_url, conn)


if __name__ == "__main__":
    asyncio.run(main())
