"""Forward request-level headers to MCP and custom tools from one service."""

from __future__ import annotations

import os
from datetime import timedelta
from functools import lru_cache
from typing import Any
from uuid import uuid4

import httpx
from deepagents import create_deep_agent
from fastapi import Body, FastAPI, Header
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import tool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolRuntime

BUILTIN_TOOLS = frozenset(
    {
        "write_todos",
        "ls",
        "read_file",
        "write_file",
        "edit_file",
        "glob",
        "grep",
        "execute",
        "task",
    }
)

app = FastAPI(title="DeepAgents dynamic tool headers demo")


def tool_name(tool: Any) -> str | None:
    if isinstance(tool, dict):
        name = tool.get("name")
        return name if isinstance(name, str) else None
    name = getattr(tool, "name", None)
    return name if isinstance(name, str) else None


class DisableBuiltinTools(AgentMiddleware):
    def wrap_model_call(self, request, handler):
        tools = [tool for tool in request.tools if tool_name(tool) not in BUILTIN_TOOLS]
        return handler(request.override(tools=tools))

    async def awrap_model_call(self, request, handler):
        tools = [tool for tool in request.tools if tool_name(tool) not in BUILTIN_TOOLS]
        return await handler(request.override(tools=tools))


def mcp_http_client(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=headers, timeout=timeout, auth=auth, trust_env=False)


async def load_profile_tools(headers: dict[str, str]):
    client = MultiServerMCPClient(
        {
            "profile": {
                "transport": "streamable_http",
                "url": os.environ.get("PROFILE_MCP_SERVER_URL", "http://127.0.0.1:8014/mcp"),
                "headers": headers,
                "timeout": timedelta(seconds=30),
                "sse_read_timeout": timedelta(seconds=300),
                "httpx_client_factory": mcp_http_client,
            }
        }
    )
    return await client.get_tools()


@lru_cache
def build_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ["MODEL_NAME"],
        api_key=os.environ["MODEL_API_KEY"],
        base_url=os.environ.get("MODEL_BASE_URL") or None,
        http_client=httpx.Client(trust_env=False),
        extra_body={
            "thinking": {"type": "disabled"},  # DeepSeek：关闭 thinking。
            "chat_template_kwargs": {"enable_thinking": False},  # 自部署模型服务：关闭 chat template thinking。
        },
    )


def get_dynamic_token(static_token: str) -> str:
    """Return a short-lived token from a service-held static token."""
    if static_token == "static-profile-secret":
        return "dynamic-profile-token"
    return f"dynamic-{static_token[-8:]}"


@tool
def get_current_user_profile_from_api(runtime: ToolRuntime[dict[str, Any], Any]) -> dict[str, str]:
    """Get the current user's profile from the internal profile API."""
    headers = runtime.context["headers"]
    tenant_id = headers.get("X-Tenant-Id", "default")
    authorization = headers.get("Authorization")
    cookie = headers.get("Cookie")
    service_authorization = headers.get("X-Service-Authorization")

    if authorization == "Bearer token-alice" or (cookie and "session=alice" in cookie):
        user_id = "alice"
    elif authorization == "Bearer token-bob" or (cookie and "session=bob" in cookie):
        user_id = "bob"
    else:
        user_id = "anonymous"

    profiles = {
        ("alice", "acme"): {
            "user_id": "alice",
            "tenant_id": "acme",
            "display_name": "Alice Chen",
            "plan": "team",
        },
        ("bob", "acme"): {
            "user_id": "bob",
            "tenant_id": "acme",
            "display_name": "Bob Lin",
            "plan": "free",
        },
    }
    profile = profiles.get(
        (user_id, tenant_id),
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "display_name": "Guest",
            "plan": "unknown",
        },
    )
    profile["service_token_status"] = (
        "ok"
        if service_authorization == "Bearer dynamic-profile-token"
        or (service_authorization and service_authorization.startswith("Bearer dynamic-"))
        else "missing"
    )
    return profile


def build_mcp_agent(tools):
    return create_deep_agent(
        model=build_model(),
        tools=tools,
        system_prompt="""
        你是资料助手。需要当前用户资料时，调用 get_current_user_profile。
        不要询问、猜测或输出 Authorization、Cookie、X-Service-Authorization 等 header。
        """.strip(),
        middleware=[DisableBuiltinTools()],
    )


@lru_cache
def get_custom_tool_agent():
    return create_deep_agent(
        model=build_model(),
        tools=[get_current_user_profile_from_api],
        system_prompt="""
        你是资料助手。需要当前用户资料时，调用 get_current_user_profile_from_api。
        不要询问、猜测或输出 Authorization、Cookie、X-Service-Authorization 等 header。
        """.strip(),
        middleware=[DisableBuiltinTools()],
    )


@app.post("/chat/mcp")
async def chat_with_mcp_tools(
    message: str = Body(..., embed=True),
    authorization: str = Header(default=""),
    cookie: str = Header(default=""),
    x_tenant_id: str = Header(default=""),
    x_thread_id: str | None = Header(default=None),
):
    tools = await load_profile_tools(
        {
            "Authorization": authorization,
            "Cookie": cookie,
            "X-Tenant-Id": x_tenant_id,
            "X-Service-Authorization": (
                f"Bearer {get_dynamic_token(os.environ['PROFILE_STATIC_TOKEN'])}"
                if os.environ.get("PROFILE_STATIC_TOKEN")
                else ""
            ),
        }
    )
    agent = build_mcp_agent(tools)
    thread_id = x_thread_id or f"thread-{uuid4().hex}"

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": thread_id}},
    )

    return result


@app.post("/chat/custom-tool")
async def chat_with_custom_tool(
    message: str = Body(..., embed=True),
    authorization: str = Header(default=""),
    cookie: str = Header(default=""),
    x_tenant_id: str = Header(default=""),
    x_thread_id: str | None = Header(default=None),
):
    thread_id = x_thread_id or f"thread-{uuid4().hex}"

    result = await get_custom_tool_agent().ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        context={
            "headers": {
                "Authorization": authorization,
                "Cookie": cookie,
                "X-Tenant-Id": x_tenant_id,
                "X-Service-Authorization": (
                    f"Bearer {get_dynamic_token(os.environ['PROFILE_STATIC_TOKEN'])}"
                    if os.environ.get("PROFILE_STATIC_TOKEN")
                    else ""
                ),
            }
        },
        config={"configurable": {"thread_id": thread_id}},
    )

    return result
