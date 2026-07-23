import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stats import calc_ping_stats, calc_tcp_stats, calc_http_stats, calc_speed_stats, get_latest_status, get_ping_dataframe, get_tcp_dataframe, get_speed_dataframe
from view import create_latency_chart, create_loss_chart, create_latency_vs_loss, create_tcp_status_chart, create_speed_chart, create_summary_table

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitor.pid')


def is_daemon_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


st.set_page_config(
    page_title="代理节点监控面板",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'daemon_started' not in st.session_state:
    if not is_daemon_running():
        from monitor import MonitorThread
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
        thread = MonitorThread(config_path)
        thread.start()
        st.session_state.daemon_started = True
        st.session_state.monitor_thread = thread
        time.sleep(2)
    else:
        st.session_state.daemon_started = True

st.title("📡 代理节点网络监控面板")

st.sidebar.header("⚙️ 目标配置")
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
if os.path.exists(config_path):
    from monitor import Config
    cfg = Config(config_path)
    st.sidebar.metric("目标 IP", cfg.target_ip)
    st.sidebar.metric("监控端口", ", ".join(str(p) for p in cfg.target_ports))
    st.sidebar.metric("监控间隔", f"{cfg.interval} 秒")

st.sidebar.header("🔧 后台服务")
if is_daemon_running():
    st.sidebar.success("✅ 后台监控运行中")
else:
    st.sidebar.warning("⚠️ 临时监控模式 (关闭页面后停止)")

st.sidebar.header("⏱️ 时间范围")
time_range = st.sidebar.selectbox(
    "选择统计时间范围",
    options=[1, 6, 12, 24, 72],
    format_func=lambda x: f"{x} 小时",
    index=2
)

st.sidebar.header("🔄 刷新")
auto_refresh = st.sidebar.checkbox("自动刷新 (每10秒)", value=True)
if auto_refresh:
    refresh_interval = st.sidebar.slider("刷新间隔 (秒)", 5, 60, 10)
else:
    refresh_interval = None

if st.sidebar.button("🔄 立即刷新"):
    st.rerun()

latest = get_latest_status()
ping_stats = calc_ping_stats(time_range)
tcp_stats = calc_tcp_stats(time_range)
http_stats = calc_http_stats(time_range)
speed_stats = calc_speed_stats(time_range)

st.header("📊 实时状态")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    if latest['ping']:
        avg_ms = latest['ping']['avg_ms']
    else:
        avg_ms = 0
    st.metric("当前延迟", f"{avg_ms} ms")

with col2:
    if latest['ping']:
        loss = latest['ping']['loss_pct']
    else:
        loss = 100
    st.metric("丢包率", f"{loss}%")

with col3:
    jitter = ping_stats['jitter']
    st.metric("抖动", f"{jitter} ms")

with col4:
    if latest.get('speed'):
        dl_speed = latest['speed']['download_mbps']
    else:
        dl_speed = 0
    st.metric("当前网速", f"{dl_speed} Mbps")

with col5:
    stats_avg_dl = speed_stats['avg_dl']
    st.metric(f"平均网速", f"{stats_avg_dl} Mbps")

with col6:
    from stats import get_ping_dataframe as gpdf
    df_check = get_ping_dataframe(time_range)
    if not df_check.empty and len(df_check) > 0:
        successful = len(df_check[df_check['loss_pct'] < 100])
        availability = round(successful / len(df_check) * 100, 1)
    else:
        availability = 0
    st.metric("可用率", f"{availability}%")

st.markdown("---")

st.header("📈 延迟与丢包")

df_ping = get_ping_dataframe(time_range)

tab1, tab2, tab3 = st.tabs(["延迟曲线", "丢包率", "延迟 vs 丢包"])

with tab1:
    st.plotly_chart(create_latency_chart(df_ping), use_container_width=True)

with tab2:
    st.plotly_chart(create_loss_chart(df_ping), use_container_width=True)

with tab3:
    st.plotly_chart(create_latency_vs_loss(df_ping), use_container_width=True)

st.markdown("---")

st.header("🔌 TCP 端口状态")

df_tcp = get_tcp_dataframe(time_range)

if not df_tcp.empty:
    ports = sorted(df_tcp['port'].unique())
    tcp_cols = st.columns(len(ports))

    for i, port in enumerate(ports):
        port_df = df_tcp[df_tcp['port'] == port]
        latest_row = port_df.iloc[-1] if len(port_df) > 0 else None

        with tcp_cols[i]:
            if latest_row is not None:
                status_icon = "✅" if latest_row['connected'] else "❌"
                st.metric(
                    f"{status_icon} 端口 {port}",
                    f"{latest_row['connect_time_ms']:.1f} ms" if latest_row['connected'] else "不可达"
                )
                success_count = len(port_df[port_df['connected'] == 1])
                total_count = len(port_df)
                avail = round(success_count / total_count * 100, 1) if total_count > 0 else 0
                st.caption(f"可用率: {avail}% ({success_count}/{total_count})")

st.plotly_chart(create_tcp_status_chart(df_tcp), use_container_width=True)

st.markdown("---")

st.header("🌐 网速测试")

df_speed = get_speed_dataframe(time_range)
st.plotly_chart(create_speed_chart(df_speed), use_container_width=True)

st.markdown("---")

st.header("📋 统计摘要")

col_left, col_right = st.columns([3, 2])

with col_left:
    st.plotly_chart(create_summary_table(ping_stats, tcp_stats, http_stats, speed_stats), use_container_width=True)

with col_right:
    st.subheader("🎯 告警状态")
    alerts = []

    if ping_stats['loss_pct'] > 10:
        alerts.append(f"🔴 丢包率过高: {ping_stats['loss_pct']}% (>10%)")
    elif ping_stats['loss_pct'] > 5:
        alerts.append(f"🟡 丢包率偏高: {ping_stats['loss_pct']}% (>5%)")

    if ping_stats['avg'] > 500:
        alerts.append(f"🔴 平均延迟过高: {ping_stats['avg']} ms (>500ms)")
    elif ping_stats['avg'] > 200:
        alerts.append(f"🟡 平均延迟偏高: {ping_stats['avg']} ms (>200ms)")

    if ping_stats['jitter'] > 50:
        alerts.append(f"🟡 抖动较大: {ping_stats['jitter']} ms (>50ms)")

    for port, data in tcp_stats.items():
        if data['availability'] < 90:
            alerts.append(f"🔴 端口 {port} 可用率低: {data['availability']}% (<90%)")
        elif data['availability'] < 99:
            alerts.append(f"🟡 端口 {port} 可用率偏低: {data['availability']}% (<99%)")

    for url, data in http_stats.items():
        if data['availability'] < 90:
            alerts.append(f"🔴 {url} 可用率低: {data['availability']}% (<90%)")

    if not alerts:
        st.success("✅ 所有指标正常，无告警")

    for alert in alerts:
        if '🔴' in alert:
            st.error(alert)
        else:
            st.warning(alert)

    st.subheader("💾 数据导出")
    st.download_button(
        "📥 导出 Ping 数据 (CSV)",
        data=df_ping.to_csv(index=False).encode('utf-8-sig'),
        file_name=f"ping_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    if not df_tcp.empty:
        st.download_button(
            "📥 导出 TCP 数据 (CSV)",
            data=df_tcp.to_csv(index=False).encode('utf-8-sig'),
            file_name=f"tcp_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

st.markdown("---")
st.caption(f"📡 监控运行中 | 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if auto_refresh and refresh_interval:
    time.sleep(refresh_interval)
    st.rerun()
