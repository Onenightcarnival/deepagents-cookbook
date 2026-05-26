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
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    response = model.invoke(
        [
            SystemMessage(content="你是一个简洁、可靠的中文技术助手。"),
            HumanMessage(content="用一句话说明 DeepAgents cookbook 的用途。"),
        ]
    )

    print(response.content)


if __name__ == "__main__":
    main()
