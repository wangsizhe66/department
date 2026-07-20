import re
from typing import List

def parse_user_input(text: str) -> List[str]:
    """
    解析用户输入的部门名称，支持：
    - 换行、逗号（中英文）、顿号、空格（含多个连续空格）等分隔符
    """
    if not text or not text.strip():
        return []
    # 使用正则分割：中文逗号、英文逗号、顿号、换行、空白（空格/制表符等）
    parts = re.split(r'[，,\n、\s]+', text.strip())
    # 过滤空字符串并去除首尾空白
    return [p.strip() for p in parts if p.strip()]