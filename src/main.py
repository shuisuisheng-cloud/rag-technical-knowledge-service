from document_loader import load_markdown_directory


def main():
    directory_path = "docs_raw"

    documents = load_markdown_directory(directory_path)

    print("文档总数：", len(documents))

    for document in documents:
        # 打印当前文档的 source
        print("文件来源:",document["metadata"]["source"])

    if documents:
        print("第一篇正文预览：")
        # 打印第一篇文档 content 的前 200 个字符
        print(documents[0]["content"][:200])
        first_document = documents[0]

    print("第一篇标题：", first_document["metadata"].get("title"))
    print("第一篇状态：", first_document["metadata"].get("status"))
    print("第一篇来源：", first_document["metadata"].get("source"))
    print("第一篇类型：", first_document["metadata"].get("file_type"))
    print("第一篇正文预览：")
    print(first_document["content"][:200])

if __name__ == "__main__":
    main()