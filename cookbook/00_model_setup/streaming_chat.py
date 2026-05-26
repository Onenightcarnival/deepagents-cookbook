import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


def main() -> None:
    load_dotenv(".env")

    model = ChatOpenAI(
        api_key=os.environ["MODEL_API_KEY"],
        base_url=os.environ["MODEL_BASE_URL"],
        model=os.environ["MODEL_NAME"],
        streaming=True,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    chunks = model.stream(
        [
            SystemMessage(content="你是一个简洁、可靠的中文技术助手。"),
            HumanMessage(content="列出从零构建 agent 的前三个步骤，每步不超过 12 个字。"),
        ]
    )

    for chunk in chunks:
        print(chunk.content, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
