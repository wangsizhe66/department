import streamlit as st
import pandas as pd
from cache_manager import CacheManager
from llm_chain import get_sorted_short_names
from utils import parse_user_input
import config

st.set_page_config(page_title="部门简称排序助手", page_icon="📋", layout="wide")

# 自定义CSS美化
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 600; color: #2c3e50; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #7f8c8d; margin-bottom: 1.5rem; }
    .result-box { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; }
    .stTextArea textarea { font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📋 部门简称排序助手</div>', unsafe_allow_html=True)

cache_mgr = CacheManager()

# ---------- 侧边栏 ----------
with st.sidebar:
    st.header("📤 上传表格")
    uploaded_file = st.file_uploader(
        "支持 CSV 或 Excel",
        type=["csv", "xlsx", "xls"],
        help="表格需包含列：序号、部门名称、部门简称、部门分类、部门定位、分类"
    )
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            required_cols = ['序号', '部门名称', '部门简称', '部门分类', '部门定位', '分类']
            if not all(col in df.columns for col in required_cols):
                st.error(f"表格缺少必要列：{', '.join(required_cols)}")
            else:
                cache_mgr.save_table(df)
                cache_mgr.clear_query_cache()
                st.success("✅ 表格已上传并缓存")
        except Exception as e:
            st.error(f"读取失败：{e}")

    st.divider()
    st.caption("缓存位置：`./cache/`")
    if st.button("🗑️ 清空所有缓存", use_container_width=True):
        for p in [config.TABLE_CACHE_PATH, config.TABLE_HASH_PATH, config.QUERY_CACHE_PATH]:
            if p.exists():
                p.unlink()
        st.success("缓存已清空")
        st.rerun()

# ---------- 加载表格 ----------
df = cache_mgr.load_table()
if df is None:
    st.warning("⚠️ 请先在左侧上传表格")
    st.stop()

# 统计信息（含二级正/副数量）
total = len(df)
dept_pos_counts = df['部门定位'].value_counts()
cnt_zheng = dept_pos_counts.get('二级正', 0)
cnt_fu = dept_pos_counts.get('二级副', 0)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("📊 总部门数", total)
with col2:
    st.metric("🎯 二级正", cnt_zheng)
with col3:
    st.metric("🔹 二级副", cnt_fu)
with col4:
    st.metric("📌 唯一简称数", df['部门简称'].nunique())

with st.expander("📋 预览全部部门数据", expanded=False):
    st.dataframe(df, use_container_width=True)

# ---------- 输入区 ----------
st.markdown("---")
st.subheader("🔍 输入部门名称")
st.caption("支持多种分隔符：换行、逗号（中英文）、顿号、空格（可多个）")

user_input_text = st.text_area(
    label="",
    placeholder="例如：\n财务部、市场部  人力资源部\n或者：财务部,市场部，人力资源部",
    height=120,
    key="input_area"
)

col_btn, _ = st.columns([1, 4])
with col_btn:
    run_btn = st.button("🚀 排序输出", type="primary", use_container_width=True)

# ---------- 处理结果 ----------
if run_btn:
    if not user_input_text.strip():
        st.error("请输入至少一个部门名称")
    else:
        inputs = parse_user_input(user_input_text)
        if not inputs:
            st.error("未能解析到有效部门名称，请检查格式")
        else:
            with st.spinner("🤖 正在调用模型匹配（首次查询可能需要几秒）..."):
                try:
                    result = get_sorted_short_names(df, inputs, cache_mgr)
                except Exception as e:
                    st.error(f"模型调用失败：{e}")
                    st.stop()

            st.markdown("---")
            output_list = result.get("output_list", [])
            details = result.get("details", [])
            if not output_list:
                st.warning("❌ 未匹配到任何二级正部门，请检查输入名称是否准确")
            else:
                st.success(f"✅ 匹配成功！共 {len(output_list)} 个部门（按序号升序）")
                output_text = "、".join(output_list)
                st.code(output_text, language="text", line_numbers=False)
                st.caption("💡 点击代码块右上角的复制按钮即可复制全部简称")

                # 显示匹配详情
                st.subheader("📝 匹配详情")
                if details:
                    df_details = pd.DataFrame(details)
                    show_cols = ['原始输入', '匹配状态', '匹配部门名称', '匹配部门简称', '部门定位', '纠正类型', '输出简称']
                    # 保证列存在
                    df_show = df_details[show_cols]
                    st.dataframe(df_show, use_container_width=True)
