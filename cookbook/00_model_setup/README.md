# 模型配置

先确认模型能连上。示例默认使用 DeepSeek 的 OpenAI-compatible 接口。

根目录 `.env`：

```env
MODEL_BASE_URL=https://api.deepseek.com
MODEL_API_KEY=...
MODEL_NAME=deepseek-v4-flash
```

## 运行

```bash
uv run python cookbook/00_model_setup/basic_chat.py
uv run python cookbook/00_model_setup/streaming_chat.py
```

## 文件

- `basic_chat.py`：普通调用
- `streaming_chat.py`：streaming 调用

## DeepSeek 参数

两个脚本都传入：

```python
reasoning_effort="high"
extra_body={"thinking": {"type": "enabled"}}
```

报 401 先查 `MODEL_API_KEY`，报 404 先查 `MODEL_NAME`。
