import yaml
from pathlib import Path


def load_markdown(file_path: str) -> dict:
    # 第一步：把字符串路径转换为 Path 对象
    file=Path(file_path)
    # 第二步：检查路径是否存在
    if not file.exists():
        raise FileNotFoundError(f"文件不存在：{file}")
    # 第三步：按 UTF-8 读取正文
    text=file.read_text(encoding="utf-8")
    content, parsed_metadata = parse_markdown_content(text)
    # 第四步：组织 content 和 metadata
    parsed_metadata["source"] = str(file)
    parsed_metadata["file_type"] = "markdown"
    document = {
    "content": content,
    "metadata": parsed_metadata
    }
    return document
    # 第五步：return 结果
def load_markdown_directory(directory_path: str) -> list[dict]:
    directory=Path(directory_path)
    if not directory.exists():
        raise FileNotFoundError(f"目录不存在:{directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"路径不是目录:{directory}")
    documents=[]
    for md_flie in sorted(directory.glob("*.md")):
        document=load_markdown(str(md_flie))
        documents.append(document)
    return documents

def parse_markdown_content(raw_text: str) -> tuple[str, dict]:
    if raw_text.startswith("---"):
        parts=raw_text.split("---",2)
        if len(parts) ==3:
            yaml_text = parts[1]
            content = parts[2].lstrip("\n")
            parsed_metadata = yaml.safe_load(yaml_text) or {}
            return content, parsed_metadata
        else:
            raise ValueError(f"文档Meatdata格式不完整:{raw_text}")
    else:
        return raw_text, {}