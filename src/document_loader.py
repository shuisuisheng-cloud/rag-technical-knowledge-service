from pathlib import Path


def load_markdown(file_path: str) -> dict:
    # 第一步：把字符串路径转换为 Path 对象
    file=Path(file_path)
    # 第二步：检查路径是否存在
    if not file.exists():
        raise FileNotFoundError(f"文件不存在：{file}")
    # 第三步：按 UTF-8 读取正文
    text=file.read_text(encoding="utf-8")
    # 第四步：组织 content 和 metadata
    document = {
    "content": text,
    "metadata": {
        "source": str(file),
        "file_type": "markdown"
        }
    }
    return document
    # 第五步：return 结果