from scripts.build_example_index import build_index, parse_items


def test_parse_items_accepts_chinese_and_ascii_colons() -> None:
    text = "\n".join(
        [
            "- 01_model：接入模型",
            "- 02_tools_mcp: 接入 MCP tool",
            "- not_an_example：忽略这一行",
        ]
    )

    assert parse_items(text) == [
        ("01_model", "接入模型"),
        ("02_tools_mcp", "接入 MCP tool"),
    ]


def test_build_index_writes_empty_state() -> None:
    assert build_index([]) == "# Example index\n\n暂无示例条目。\n\n共 0 个示例。\n"
