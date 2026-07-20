import re
from typing import List, Optional
import pandas as pd
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import config

llm = ChatTongyi(
    model=config.MODEL_NAME,
    temperature=config.TEMPERATURE,
    dashscope_api_key=config.DASHSCOPE_API_KEY,
)

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """你是一个部门名称匹配助手。根据提供的表格数据，用户会给出一些部门名称（可能是全称、简称或带有错别字）。
你需要找出匹配的部门，但只考虑部门定位为"二级正"的部门。
请输出这些匹配部门对应的**序号**（即表格中的“序号”列），按升序排列，用英文逗号分隔。
如果没有匹配到任何部门，请输出"无"。
只输出序号列表，不要输出其他任何内容。"""),
    ("human", "表格数据（仅包含定位为二级正的部门）：\n{table_data}\n\n用户输入的部门名称：{user_inputs}\n\n请输出匹配到的部门序号（升序，逗号分隔）")
])

def build_table_text(df_filtered: pd.DataFrame) -> str:
    cols = ['序号', '部门名称', '部门简称', '部门分类', '部门定位', '分类']
    return df_filtered[cols].to_string(index=False)

def parse_model_output(raw_output: str) -> List[int]:
    raw = raw_output.strip()
    if raw == "无" or not raw:
        return []
    numbers = re.findall(r'\d+', raw)
    if not numbers:
        return []
    return sorted(set(int(n) for n in numbers))

def get_sorted_short_names(
    df_filtered: pd.DataFrame,
    user_inputs: List[str],
    cache_mgr,
) -> List[str]:
    table_hash = cache_mgr.get_table_hash()
    if table_hash is None:
        raise RuntimeError("表格尚未缓存，请先上传表格。")
    
    cached = cache_mgr.get_query_result(user_inputs, table_hash)
    if cached is not None:
        return cached

    table_text = build_table_text(df_filtered)
    user_inputs_str = "、".join(user_inputs)

    chain = PROMPT_TEMPLATE | llm | StrOutputParser()
    response = chain.invoke({
        "table_data": table_text,
        "user_inputs": user_inputs_str,
    })

    seq_numbers = parse_model_output(response)
    if not seq_numbers:
        result = []
    else:
        idx_to_short = dict(zip(df_filtered['序号'], df_filtered['部门简称']))
        result = [idx_to_short[num] for num in seq_numbers if num in idx_to_short]

    cache_mgr.save_query_result(user_inputs, table_hash, result)
    return result