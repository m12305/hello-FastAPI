"""
3.4 异步性能对比 — 压测脚本

运行方式（需要先启动 main.py）:
    cd code/阶段3-数据库与ORM/3.4-异步数据库操作
    # 终端 1: uvicorn main:app --reload
    # 终端 2: python benchmark.py

用 50 个并发请求对比异步 API 的性能。
"""

import time
import asyncio
import httpx


async def benchmark():
    """50 个并发请求压测"""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # 并发 50 个 GET 请求
        tasks = [client.get("/users/") for _ in range(50)]

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start

        success = sum(1 for r in results if r.status_code == 200)
        print(f"\n{'='*50}")
        print(f"  并发请求: 50")
        print(f"  成功: {success}/50")
        print(f"  总耗时: {elapsed:.3f}s")
        print(f"  平均 QPS: {50 / elapsed:.0f}")
        print(f"{'='*50}")


if __name__ == "__main__":
    print("🚀 开始异步压测...")
    print("⚠️ 请确保 main.py 已在另一个终端运行")
    asyncio.run(benchmark())
