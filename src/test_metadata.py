from document_loader import validate_metadata


complete_metadata = {
    "title": "test",
    "project": "RAG",
    "system_layer": "知识层",
    "document_type": "learning_note",
    "status": "verified",
    "last_updated": "2026-07-09",
    "tags": ["Python"],
}


test_cases = [
    (
        "完整字典",
        complete_metadata,
    ),
    (
        "缺少title",
        {
            "project": "RAG",
            "system_layer": "知识层",
            "document_type": "learning_note",
            "status": "verified",
            "last_updated": "2026-07-09",
            "tags": ["Python"],
        },
    ),
    (
        "缺少tags",
        {
            "title": "test",
            "project": "RAG",
            "system_layer": "知识层",
            "document_type": "learning_note",
            "status": "verified",
            "last_updated": "2026-07-09",
        },
    ),
    (
        "列表",
        ["title", "status"],
    ),
    (
        "字符串",
        "title: test",
    ),(
    "非法status",
    {
        "title": "test",
        "project": "RAG",
        "system_layer": "知识层",
        "document_type": "learning_note",
        "status": "verify",
        "last_updated": "2026-07-09",
        "tags": ["Python"],
    },
),
(
    "tags为字符串",
    {
        "title": "test",
        "project": "RAG",
        "system_layer": "知识层",
        "document_type": "learning_note",
        "status": "verified",
        "last_updated": "2026-07-09",
        "tags": "Python",
    },
),
]


for case_name, metadata in test_cases:
    print(f"\n===== {case_name} =====")

    try:
        result = validate_metadata(
            metadata=metadata,
            source=f"{case_name}.md",
        )
        print("校验通过：", result)

    except (TypeError, ValueError) as error:
        print(f"捕获到 {type(error).__name__}:", error)