import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Business Matching Pipeline", layout="wide")

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

# === SIDEBAR ===
st.sidebar.title("控制台 (Console)")

data_source = st.sidebar.selectbox(
    "合规数据源 (Data Source)",
    ("iFinD", "Tongdaxin", "Generic")
)

api_key = st.sidebar.text_input("DeepSeek API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("上传承载地禀赋 (.xlsx)")
uploaded_file = st.sidebar.file_uploader("限制文件拖拽上传区", type=["xlsx"])


# === MAIN VIEW ===
st.title("企业扩张动能与承载地匹配系统")
st.markdown("通过多源异构数据与大模型驱动，实现区域禀赋与高分企业需求精准匹配。")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. 综合评定雷达图")
    # Using the instructions strictly: "物理产能饱度", "财务扩张支撑力", "本地扩张受限度", "战略意图得分"
    categories = ['物理产能饱度', '财务扩张支撑力', '本地扩张受限度', '战略意图得分']

    # Mock scores for a hypothetical top-selected company for illustration
    scores = [0.8, 0.9, 0.6, 0.85]

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=scores + [scores[0]], # Close the loop
        theta=categories + [categories[0]],
        fill='toself',
        name='Tech Corp A'
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        title="企业综合扩张动能雷达图"
    )
    st.plotly_chart(fig_radar, use_container_width=True)


with col2:
    st.subheader("2. 历史周期折线图 (10年)")

    company_code = st.text_input("输入企业代码 (例如: 000001.SZ)", value="000001.SZ")

    if st.button("拉取企业财务数据"):
        with st.spinner("Fetching data from backend..."):
            try:
                response = requests.post(f"{API_BASE_URL}/etl/fetch", json={
                    "source": data_source,
                    "company_code": company_code
                })
                if response.status_code == 200:
                    data = response.json().get("data", [])
                    df = pd.DataFrame(data)

                    if not df.empty:
                        # 映射“营业收入”、“净利润”与“资产负债率”三项核心财务指标
                        # Assuming the backend returns standard english names as defined in Phase 2
                        df_plot = df.rename(columns={
                            'revenue': '营业收入',
                            'net_profit': '净利润',
                            'liability_ratio': '资产负债率',
                            'year': '年份'
                        })

                        # We use two y-axes because liability ratio is a small decimal,
                        # while revenue/profit are large numbers.
                        fig_line = go.Figure()

                        fig_line.add_trace(go.Scatter(x=df_plot['年份'], y=df_plot['营业收入'], mode='lines+markers', name='营业收入'))
                        fig_line.add_trace(go.Scatter(x=df_plot['年份'], y=df_plot['净利润'], mode='lines+markers', name='净利润'))

                        fig_line.add_trace(go.Scatter(x=df_plot['年份'], y=df_plot['资产负债率'], mode='lines+markers', name='资产负债率', yaxis='y2'))

                        fig_line.update_layout(
                            title=f"{company_code} - 过去十年核心财务指标",
                            xaxis_title="年份",
                            yaxis=dict(title="金额"),
                            yaxis2=dict(title="比率", overlaying='y', side='right'),
                            hovermode="x unified"
                        )
                        st.plotly_chart(fig_line, use_container_width=True)
                    else:
                        st.warning("No data found for the given parameters.")
                else:
                    st.error(f"Error fetching data: {response.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

st.markdown("---")
st.subheader("3. 动态业务要素匹配结果")

if uploaded_file is not None:
    st.info(f"已上传文件: {uploaded_file.name}. 正在进行矩阵计算匹配...")

    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key

        response = requests.post(f"{API_BASE_URL}/business/match", files=files, headers=headers)

        if response.status_code == 200:
            matches = response.json().get("matches", [])
            df_matches = pd.DataFrame(matches)

            if not df_matches.empty:
                st.dataframe(
                    df_matches.style.background_gradient(subset=['match_score'], cmap='Blues'),
                    use_container_width=True
                )

                # Plot bar chart of top matches
                fig_bar = px.bar(df_matches, x='match_score', y='enterprise_name', color='region_name', orientation='h', title='区域与企业契合度评分排行')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.warning("No matches generated.")
        else:
            st.error(f"Matching failed: {response.text}")

    except Exception as e:
        st.error(f"Error during matching request: {e}")
else:
    st.info("请在左侧侧边栏上传区域承载地约束条件（.xlsx 文件）以查看计算矩阵结果。")