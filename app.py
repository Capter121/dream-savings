import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 1. 页面配置与连接 ---
st.set_page_config(page_title="云端梦想储蓄罐", page_icon="☁️", layout="wide")

# 尝试连接数据库 (需要安装 st-supabase-connection)
try:
    from st_supabase_connection import SupabaseConnection
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("请确保已安装 st-supabase-connection 并配置 secrets.toml")

# --- 2. 侧边栏：登录与全局配置 ---
with st.sidebar:
    st.header("👤 个人云端同步")
    user_key = st.text_input("输入你的专属同步密钥", type="password", help="不同密钥对应不同的储蓄计划")
    
    if not user_key:
        st.warning("请输入密钥以加载或创建你的云端空间")
        st.stop()

    st.divider()
    st.header("⚙️ 储蓄配置")
    
    # 从云端读取初始值或设置默认值
    # 注意：实际开发中这里会先查询数据库，此处简化为交互输入
    daily_saving = st.number_input("每日固定存款 (元)", min_value=1.0, value=50.0)
    current_balance = st.number_input("当前已有总额 (元)", min_value=0.0, value=0.0)
    
    if st.button("🚀 保存/同步到云端", use_container_width=True):
        # 封装数据上传云端
        data_to_save = {
            "user_id": user_key,
            "wish_list": st.session_state.get('wish_list', []),
            "current_balance": current_balance,
            "daily_saving": daily_saving
        }
        conn.table("savings_data").upsert(data_to_save).execute()
        st.success("云端同步成功！")

# --- 3. 初始化数据 (Session State) ---
# 首次登录尝试从云端拉取
if f"loaded_{user_key}" not in st.session_state:
    response = conn.table("savings_data").select("*").eq("user_id", user_key).execute()
    if response.data:
        record = response.data[0]
        st.session_state.wish_list = record.get('wish_list', [])
        st.session_state[f"loaded_{user_key}"] = True
    else:
        st.session_state.wish_list = []
        st.session_state[f"loaded_{user_key}"] = True

# --- 4. 愿望添加逻辑 ---
st.title(f"💰 {user_key} 的梦想储蓄计划")

col_input, col_stats = st.columns([1, 2])

with col_input:
    st.markdown("### ➕ 添加新愿望")
    with st.form("add_wish_form", clear_on_submit=True):
        name = st.text_input("想要什么？")
        price = st.number_input("大概金额 (元)", min_value=1.0)
        submit = st.form_submit_button("添加到清单")
        
        if submit and name:
            st.session_state.wish_list.append({"name": name, "price": price})
            st.rerun()

# --- 5. 核心计算与显示 ---
if st.session_state.wish_list:
    # 逻辑计算
    temp_balance = current_balance
    display_list = []
    total_days_acc = 0
    
    for item in st.session_state.wish_list:
        needed = item['price']
        already_have = min(temp_balance, needed)
        gap = max(0.0, needed - already_have)
        days = int(gap / daily_saving) if daily_saving > 0 else 0
        
        finish_date = datetime.now() + timedelta(days=total_days_acc + days)
        
        display_list.append({
            "name": item['name'],
            "target": needed,
            "progress": (already_have / needed),
            "days": days,
            "date": finish_date.strftime("%Y-%m-%d")
        })
        
        temp_balance = max(0.0, temp_balance - needed)
        total_days_acc += days

    # 渲染卡片
    tab1, tab2 = st.tabs(["📋 愿望详情", "📊 周期预测"])
    
    with tab1:
        for i, wish in enumerate(display_list):
            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{i+1}. {wish['name']}** (￥{wish['target']:,.2f})")
                c2.caption(f"📅 预计达成: {wish['date']}")
                st.progress(wish['progress'])
                if st.button(f"删除 {wish['name']}", key=f"del_{i}"):
                    st.session_state.wish_list.pop(i)
                    st.rerun()
                st.divider()

    with tab2:
        df = pd.DataFrame(display_list)
        st.subheader("累计达成所需天数")
        st.bar_chart(df.set_index("name")["days"])
        
        total_needed = sum(w['target'] for w in display_list)
        total_gap = max(0.0, total_needed - current_balance)
        st.metric("总愿望达成预计耗时", f"{total_days_acc} 天", delta=f"总缺口 ￥{total_gap:,.2f}")

else:
    st.info("清单空空如也，快去添加你的第一个愿望吧！")

# --- 底部美化 ---
st.markdown("---")
st.caption("✨ 数据实时存储于 Supabase 云端 | 支持分布式跨设备访问")