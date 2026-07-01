from document_loader import load_markdown
def main():
    # 1. 指定要读取的 Markdown 文件
    file_path = "docs_raw/stm32_terminal_overview.md"

    # 2. 调用函数，接收返回的文档字典
    document = load_markdown(file_path)

    # 3. 查看文档来源和类型
    print("文档来源：", document["metadata"]["source"])
    print("文件类型：", document["metadata"]["file_type"])

    # 4. 只显示正文前 200 个字符
    print("正文预览：")
    print(document["content"][:200])

if __name__=="__main__":
    main()