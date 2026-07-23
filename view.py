import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from plotly.subplots import make_subplots


def create_latency_chart(df):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=350, title="延迟趋势")
        return fig

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['avg_ms'],
        mode='lines+markers', name='平均延迟',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=4)
    ))

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['max_ms'],
        mode='lines', name='最大延迟',
        line=dict(color='#ff7f0e', width=1, dash='dot'),
        opacity=0.6
    ))

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['min_ms'],
        mode='lines', name='最小延迟',
        line=dict(color='#2ca02c', width=1, dash='dot'),
        opacity=0.6
    ))

    fig.update_layout(
        title='延迟趋势 (ms)',
        xaxis_title='时间',
        yaxis_title='延迟 (ms)',
        height=400,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_loss_chart(df):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=300, title="丢包率趋势")
        return fig

    fig = go.Figure()

    colors = ['#2ca02c' if v < 5 else '#ff7f0e' if v < 20 else '#d62728' for v in df['loss_pct']]

    fig.add_trace(go.Bar(
        x=df['timestamp'], y=df['loss_pct'],
        marker_color=colors, name='丢包率',
        text=[f'{v}%' for v in df['loss_pct']],
        textposition='outside'
    ))

    fig.add_hline(y=10, line_dash="dash", line_color="red", annotation_text="10% 告警线")

    fig.update_layout(
        title='丢包率 (%)',
        xaxis_title='时间',
        yaxis_title='丢包率 (%)',
        height=300,
        yaxis=dict(range=[0, max(max(df['loss_pct']) + 10, 15)]),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_latency_vs_loss(df):
    if df.empty or len(df) < 2:
        fig = go.Figure()
        fig.add_annotation(text="数据不足", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=300, title="延迟 vs 丢包")
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['avg_ms'],
        mode='lines', name='延迟 (ms)',
        line=dict(color='#1f77b4', width=2)
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['loss_pct'],
        mode='lines', name='丢包率 (%)',
        line=dict(color='#d62728', width=2)
    ), secondary_y=True)

    fig.update_xaxes(title_text='时间')
    fig.update_yaxes(title_text='延迟 (ms)', secondary_y=False, gridcolor='lightgray')
    fig.update_yaxes(title_text='丢包率 (%)', secondary_y=True, gridcolor='lightgray')

    fig.update_layout(
        title='延迟与丢包率对比',
        height=350,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_tcp_status_chart(df):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=250, title="TCP 端口状态")
        return fig

    ports = df['port'].unique()

    fig = go.Figure()

    for port in sorted(ports):
        port_df = df[df['port'] == port]
        fig.add_trace(go.Scatter(
            x=port_df['timestamp'], y=port_df['connect_time_ms'],
            mode='markers', name=f'端口 {port}',
            marker=dict(
                size=8,
                color=port_df['connected'].apply(lambda x: '#2ca02c' if x else '#d62728'),
                symbol=port_df['connected'].apply(lambda x: 'circle' if x else 'x')
            )
        ))

    fig.update_layout(
        title='TCP 端口连接耗时 (ms)',
        xaxis_title='时间',
        yaxis_title='耗时 (ms)',
        height=300,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_speed_chart(df):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="暂无网速数据", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(height=300, title="下载速度趋势")
        return fig

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['download_mbps'],
        mode='lines+markers', name='下载速度',
        line=dict(color='#9467bd', width=2.5),
        marker=dict(size=6, color='#9467bd'),
        fill='tozeroy',
        fillcolor='rgba(148,103,189,0.15)'
    ))

    fig.update_layout(
        title='下载速度趋势 (Mbps)',
        xaxis_title='时间',
        yaxis_title='速度 (Mbps)',
        height=300,
        hovermode='x unified',
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig


def create_summary_table(ping_stats, tcp_stats, http_stats, speed_stats=None):
    fig = go.Figure()

    cells = [['指标', '值'], [], []]
    header_color = ['#1f77b4', '#1f77b4']

    names = []
    values = []

    names.append('<b>ICMP Ping</b>')
    values.append('')
    for k, v in ping_stats.items():
        if k == 'sample_count':
            continue
        label_map = {
            'avg': '平均延迟', 'median': '中位数', 'min': '最小延迟',
            'max': '最大延迟', 'std_dev': '标准差', 'loss_pct': '丢包率',
            'jitter': '抖动'
        }
        names.append(f'  {label_map.get(k, k)}')
        values.append(f'{v} ms' if k != 'loss_pct' else f'{v}%')
    names.append(f'  采样数')
    values.append(f'{ping_stats["sample_count"]} 次')

    names.append('<b></b>')
    values.append('')

    names.append('<b>TCP 端口</b>')
    values.append('')
    for port, data in sorted(tcp_stats.items()):
        names.append(f'  端口 {port} 可用率')
        values.append(f'{data["availability"]}%')
        names.append(f'  端口 {port} 平均延迟')
        values.append(f'{data["avg_connect_time_ms"]} ms')

    if speed_stats and speed_stats.get('sample_count', 0) > 0:
        names.append('<b></b>')
        values.append('')

        names.append('<b>网速测试</b>')
        values.append('')
        names.append('  平均下载速度')
        values.append(f'{speed_stats["avg_dl"]} Mbps')
        names.append('  最大下载速度')
        values.append(f'{speed_stats["max_dl"]} Mbps')
        names.append('  最小下载速度')
        values.append(f'{speed_stats["min_dl"]} Mbps')
        names.append(f'  测试次数')
        values.append(f'{speed_stats["sample_count"]} 次')

    names.append('<b></b>')
    values.append('')

    names.append('<b>HTTP 服务</b>')
    values.append('')
    for url, data in http_stats.items():
        names.append(f'  {url} 可用率')
        values.append(f'{data["availability"]}%')
        names.append(f'  {url} 平均响应')
        values.append(f'{data["avg_response_ms"]} ms')

    fig.add_trace(go.Table(
        header=dict(
            values=['指标', '值'],
            fill_color='#1f77b4',
            font=dict(color='white', size=13),
            align='left',
            height=35
        ),
        cells=dict(
            values=[names, values],
            fill_color=[['#f8f9fa'] * len(names), ['white'] * len(names)],
            font=dict(size=12),
            align='left',
            height=28
        )
    ))

    fig.update_layout(
        title='统计摘要',
        height=max(400, len(names) * 30 + 80),
        margin=dict(l=20, r=20, t=40, b=20)
    )

    return fig
