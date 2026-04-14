import asyncio
import json

from src.query_client.nats_client import RAGTasksClient

nats_client = RAGTasksClient()


async def index_handler(msg):
    try:
        data = json.loads(msg.data.decode("utf-8"))
        task_id = data["task_id"]
        # payload = data["payload"]

        print(f"[IndexWorker] Получена задача {task_id} (type={data.get('type')})")

        # 1. Чанкинг
        # 2. ApiClient.get_embedding(...) для чанков
        # 3. QdrantVectorClient.upsert(...)
        # 4. RedisClient.update_status(task_id, "completed")

        await msg.ack()
        print(f"[IndexWorker] Задача {task_id} успешно завершена")

    except Exception as e:
        print(f"[IndexWorker] Ошибка: {e}")
        await msg.nak()


async def run():
    """Запуск index + rebuild consumer'ов (один durable)"""
    await nats_client.connect()

    # Подписываемся на два subject'а с одним durable consumer'ом
    await nats_client.subscribe(
        subject="tasks.rag.index", durable="index-worker", handler=index_handler, max_ack_pending=1
    )
    await nats_client.subscribe(
        subject="tasks.rag.rebuild",
        durable="index-worker",  # тот же durable!
        handler=index_handler,
        max_ack_pending=1,
    )

    print("✅ IndexWorker запущен (index + rebuild)")
    await asyncio.Future()
