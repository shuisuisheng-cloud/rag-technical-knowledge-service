import yaml
from pathlib import Path


def load_markdown(file_path: str) -> dict:
    file=Path(file_path)
    if not file.exists():
        raise FileNotFoundError(f"文件不存在：{file}")
    text=file.read_text(encoding="utf-8")
    content, parsed_metadata = parse_markdown_content(text)
    parsed_metadata = validate_metadata(
    parsed_metadata,
    str(file),)
    parsed_metadata["source"] = str(file)
    parsed_metadata["file_type"] = "markdown"
    document = {
    "content": content,
    "metadata": parsed_metadata
    }
    return document
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

def parse_markdown_content(raw_text: str) -> tuple[str, object]:
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

def validate_metadata(metadata: object, source: str) -> dict:
    if not isinstance(metadata, dict):
        raise TypeError(f"metadata不是字典:{source},实际类型为{type(metadata).__name__}")
    required_fields = ["title","project","system_layer","document_type","status","last_updated","tags"]
    allowed_status = {"in_progress","completed","verified","software_verified","sample_verified"}

    for field in required_fields:
        if field not in metadata:
            raise ValueError( f"Metadata缺少必需字段: source={source}, field={field}")
    if metadata["status"] not in allowed_status:
        raise ValueError(f"Metadata状态非法: source={source}, "
            f"status={metadata['status']}")
    if not isinstance(metadata["tags"], list):
        raise TypeError(f"Metadata字段类型错误: source={source}, "
            f"field=tags, expected=list, "
            f"actual={type(metadata['tags']).__name__}")
    return metadata