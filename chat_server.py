import asyncio
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime

from redis import asyncio as aioredis
from redis.client import Redis, PubSub
from fastapi import WebSocket


@dataclass
class ChatMessage:
    channel_id: str
    client_id: int
    time: str
    message: str


class RedisService:
    def __init__(self):
        self.redis_host = f"{os.environ.get('REDIS_HOST', 'redis://localhost')}"

    async def get_conn(self):
        return await aioredis.from_url(self.redis_host, encoding="utf-8", decode_responses=True)


class ChatServer(RedisService):
    def __init__(self, websocket, channel_id, client_id, logger):
        super().__init__()
        self.ws: WebSocket = websocket
        self.channel_id = channel_id
        self.client_id = client_id
        self.redis = RedisService()
        self.logger = logger

    async def publish_handler(self, conn: Redis):
        try:
            while True:
                message = await self.ws.receive_text()
                if message:
                    now = datetime.now()
                    date_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    chat_message = ChatMessage(
                        channel_id=self.channel_id, client_id=self.client_id, time=date_time, message=message
                    )
                    await conn.publish(self.channel_id, json.dumps(asdict(chat_message)))
        except Exception as e:
            self.logger.error(e)

    async def subscribe_handler(self, pubsub: PubSub):
        await pubsub.subscribe(self.channel_id)
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    data = json.loads(message.get("data"))
                    chat_message = ChatMessage(**data)
                    await self.ws.send_text(f"[{chat_message.time}] {chat_message.message} ({chat_message.client_id})")
        except Exception as e:
            self.logger.error(e)

    async def run(self):
        conn: Redis = await self.redis.get_conn()
        pubsub: PubSub = conn.pubsub()

        tasks = [self.publish_handler(conn), self.subscribe_handler(pubsub)]
        results = await asyncio.gather(*tasks)

        self.logger.info(f"Done task: {results}")

