import re
from typing import List, Optional, Dict, Any
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
    ("system", """你是一个部门名称匹配助手。根据提供的表格数据，用户会给出一些部门名称（可能是全称、简称或带有错别字）。你需要为每个输入找出匹配的部门，只考虑表格中存在的部门。请按照用户输入的顺序，输出每个输入对应的部门名称（即表格中的“部门名称”列）。如果某个输入未匹配到任何部门，请输出“无”。多个结果用英文逗号分隔。只输出部门名称列表，不要输出其他内容。"""),
    ("human", "表格数据：\n{table_data}\n\n用户输入的部门名称（按顺序）：{user_inputs}\n\n请输出按顺序对应的部门名称列表，用英文逗号分隔。")
])

def add_parent_info(df: pd.DataFrame) -> pd.DataFrame:
    """为DataFrame添加两列：'所属二级正简称' 和 '所属二级正序号'，仅处理二级正和二级副"""
    df_copy = df.copy()
    df_copy['所属二级正简称'] = None
    df_copy['所属二级正序号'] = None

    current_parent_short = None
    current_parent_seq = None

    for idx, row in df_copy.iterrows():
        if pd.notna(row.get('序号')) and row.get('部门定位') == '二级正':
            current_parent_short = row['部门简称']
            current_parent_seq = row['序号']
        if row.get('部门定位') in ['二级正', '二级副']:
            df_copy.at[idx, '所属二级正简称'] = current_parent_short
            df_copy.at[idx, '所属二级正序号'] = current_parent_seq
        # 其他定位（如子公司）不处理
    return df_copy

def build_table_text(df_enhanced: pd.DataFrame) -> str:
    """构建供模型阅读的表格文本（仅含二级正和二级副）"""
    mask = df_enhanced['部门定位'].isin(['二级正', '二级副'])
    df_sub = df_enhanced[mask].copy()
    cols = ['部门名称', '部门简称', '部门定位', '所属二级正简称']
    # 将 None 转为空字符串以便显示
    df_sub = df_sub.fillna('')
    return df_sub[cols].to_string(index=False)

def parse_model_output(raw_output: str) -> List[str]:
    """解析模型输出的部门名称列表，按输入顺序"""
    raw = raw_output.strip()
    if not raw:
        return []
    raw = raw.replace('，', ',')
    parts = [p.strip() for p in raw.split(',') if p.strip()]
    return parts

def get_sorted_short_names(
    df: pd.DataFrame,
    user_inputs: List[str],
    cache_mgr,
) -> Dict[str, Any]:
    table_hash = cache_mgr.get_table_hash()
    if table_hash is None:
        raise RuntimeError("表格尚未缓存，请先上传表格。")

    # 尝试从缓存获取完整结果
    cached = cache_mgr.get_query_result(user_inputs, table_hash)
    if cached is not None:
        return cached

    # 增强表格（添加归属信息）
    df_enhanced = add_parent_info(df)

    # 构建表格文本
    table_text = build_table_text(df_enhanced)
    user_inputs_str = "、".join(user_inputs)

    # 调用模型
    chain = PROMPT_TEMPLATE | llm | StrOutputParser()
    response = chain.invoke({
        "table_data": table_text,
        "user_inputs": user_inputs_str,
    })

    # 解析响应
    matched_names = parse_model_output(response)
    # 确保长度与输入一致
    if len(matched_names) < len(user_inputs):
        matched_names += ["无"] * (len(user_inputs) - len(matched_names))
    elif len(matched_names) > len(user_inputs):
        matched_names = matched_names[:len(user_inputs)]

    details = []
    output_short_set = {}  # (序号, 简称) -> 简称

    for inp, matched_name in zip(user_inputs, matched_names):
        detail = {
            "原始输入": inp,
            "匹配状态": "成功",
            "匹配部门名称": matched_name,
            "匹配部门简称": None,
            "部门定位": None,
            "所属二级正简称": None,
            "纠正类型": "",
            "输出简称": None
        }
        if matched_name == "无" or not matched_name:
            detail["匹配状态"] = "未识别"
            detail["纠正类型"] = "未识别"
            details.append(detail)
            continue

        # 在增强表中查找
        row = df_enhanced[df_enhanced['部门名称'] == matched_name]
        if row.empty:
            detail["匹配状态"] = "未识别"
            detail["纠正类型"] = "未识别（模型返回了不存在的部门）"
            details.append(detail)
            continue

        row = row.iloc[0]
        dept_short = row['部门简称'] if pd.notna(row['部门简称']) else ''
        dept_pos = row['部门定位']
        parent_short = row['所属二级正简称']
        parent_seq = row['所属二级正序号']

        detail["匹配部门简称"] = dept_short
        detail["部门定位"] = dept_pos
        detail["所属二级正简称"] = parent_short

        # 确定基础纠正类型
        if inp == matched_name:
            base = "全称转简称"
        elif inp == dept_short:
            base = "无纠正"
        else:
            base = "错别字纠正（或近似匹配）"

        # 若为二级副，附加并入信息
        if dept_pos == "二级副":
            correction = base + " + 二级副并入"
            output_short = parent_short
        else:
            correction = base
            output_short = dept_short

        detail["纠正类型"] = correction
        detail["输出简称"] = output_short
        details.append(detail)

        # 收集最终输出（按序号升序去重）
        if parent_seq is not None and parent_short is not None:
            output_short_set[(parent_seq, parent_short)] = output_short

    # 构建最终输出列表
    sorted_keys = sorted(output_short_set.keys(), key=lambda x: x[0])
    output_list = [output_short_set[key] for key in sorted_keys]

    result = {
        "output_list": output_list,
        "details": details
    }

    # 缓存结果
    cache_mgr.save_query_result(user_inputs, table_hash, result)
    return result
