from taskiq import AsyncBroker, InMemoryBroker
from taskiq_redis import ListQueueBroker

from src.core import Settings
from src.core import settings as global_settings
from src.infrastructure.messaging.transports import get_email_transport


def create_broker(settings: Settings | None = None) -> AsyncBroker:
    cfg = settings or global_settings
    if cfg.app_env == "test" or cfg.enduro_attack:
        return InMemoryBroker()
    return ListQueueBroker(
        cfg.redis_url,
        socket_timeout=None,
        socket_connect_timeout=10,
        health_check_interval=30,
    )


broker = create_broker()


@broker.task(task_name="send_email_task")
async def send_email_task(to_email: str, subject: str, body_text: str) -> None:
    transport = get_email_transport()
    await transport.send_email(to_email=to_email, subject=subject, body_text=body_text)


class TaskiqEmailQueue:
    def __init__(self, broker_instance: AsyncBroker | None = None) -> None:
        self._broker = broker_instance or broker

    async def enqueue_email(self, to_email: str, subject: str, body_text: str) -> None:
        await send_email_task.kiq(
            to_email=to_email, subject=subject, body_text=body_text
        )
