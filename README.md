# 部门简称排序助手

基于 Streamlit + LangChain + Qwen3.7-Max 的智能部门匹配工具。

## 新特性
- 输入支持多种分隔符（换行、逗号、顿号、空格等），无需严格格式
- 输出为纯文本简称列表（无序号），并置于带复制按钮的代码块，方便直接粘贴
- 界面美观，统计信息一目了然

## 安装与运行
```bash
pip install -r requirements.txt
export DASHSCOPE_API_KEY=你的Key   # 或写入 .env
streamlit run app.py