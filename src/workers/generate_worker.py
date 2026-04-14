import asyncio
import json

from src.query_client.nats_client import RAGTasksClient

nats_client = RAGTasksClient()


async def generate_handler(msg):
    try:
        data = json.loads(msg.data.decode("utf-8"))
        task_id = data["task_id"]
        # payload = data["payload"]

        print(f"[GenerateWorker] Получена задача {task_id}")

        # 1. MauticClient.get_digital_footprint(...)
        # 2. ApiClient.get_embedding(...)
        # 3. QdrantVectorClient.retrieval(...)
        # 4. ApiClient.generate_with_llm(...)
        # 5. MauticClient.save_recommendation(...)
        # 6. RedisClient.update_status(task_id, "completed")

        await msg.ack()
        print(f"[GenerateWorker] Задача {task_id} успешно завершена")

    except Exception as e:
        print(f"[GenerateWorker] Ошибка: {e}")
        await msg.nak()


async def run():
    """Запуск только generate consumer'а"""
    await nats_client.connect()
    await nats_client.subscribe(
        subject="tasks.rag.generate", durable="generate-worker", handler=generate_handler, max_ack_pending=1
    )
    print("✅ GenerateWorker запущен")
    await asyncio.Future()  # держим таску живой
