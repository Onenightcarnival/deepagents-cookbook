# 07 persistence

## 场景

agent 进入长期运行后，不能只把状态留在一次进程里。

这个示例把 DeepAgents 的 checkpoint 写到本地 PostgreSQL。

第一次运行时，用户告诉 agent 要写第 07 章持久化示例。第二次运行时，代码重新创建 agent，只传入同一个 `thread_id` 和一句“继续刚才的主题”。agent 会从 PostgreSQL 里读回之前的 checkpoint，再接着回答。

这里演示的是运行状态持久化，不是长期 memory。checkpoint 保存的是一个 thread 的运行现场，包括消息、state 和中间写入。进程重启后，只要 `thread_id` 不变，就可以继续同一个 thread。

## 代码

见 [postgres_checkpoint.py](postgres_checkpoint.py)。

## 运行方式

先确认 `.env` 里有模型变量和 PostgreSQL 变量：

```bash
MODEL_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=xxxx
MODEL_NAME=deepseek-v4-flash

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=deepagents
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

运行示例：

```bash
uv run --env-file .env python examples/07_persistence/postgres_checkpoint.py
```

第一次运行会自动创建 LangGraph checkpoint 表。命令结束前会打印两次回答，并显示本次 thread 最近写入的 checkpoint 数量。

示例使用固定的 `persistence-demo-thread` 作为 `thread_id`。重复运行同一个命令时，会继续同一个 thread。

## 关键点

- `PostgresSaver` 是 LangGraph 的 PostgreSQL checkpointer。DeepAgents 通过 `checkpointer` 参数使用它。
- `checkpointer.setup()` 会创建或迁移 checkpoint 表。第一次连接新库时要调用。
- `thread_id` 是恢复现场的关键。相同 `thread_id` 会继续同一个 thread，不同 `thread_id` 会开启新的运行现场。
- 业务系统通常不要直接把用户 id 当成 `thread_id`。更常见的做法是用任务 id、会话 id 或工单 id，再在业务表里记录它和用户 id 的关系。
- checkpoint 适合保存运行现场。长期偏好、用户画像和可检索知识，仍然应该放到 memory、数据库表或 retriever 里。

## 取舍

外置 checkpoint 适合长任务、异步任务和服务重启恢复。它也方便排查某个 thread 走到哪一步。

不要把所有业务数据都塞进 checkpoint。checkpoint 的结构服务于运行恢复，不适合作为业务查询模型。订单、客户、任务状态这类数据，仍然放在自己的业务表里。checkpoint 只保存 agent 继续运行所需的现场。
