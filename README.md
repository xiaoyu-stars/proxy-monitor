# proxy-monitor

代理节点网络监控面板 — 对目标服务器的**延迟、丢包率、TCP 端口可用性、HTTP 响应和下载网速**进行实时采集与可视化展示。

## 功能

- **ICMP Ping** — 延迟 (avg/min/max)、丢包率、抖动
- **TCP 端口** — 端口可达性、连接耗时
- **HTTP 服务** — 响应时间、可用率
- **网速测试** — 下载带宽 (Mbps)
- **统计指标** — 均值 / 中位数 / 最大 / 最小 / 标准差 / 可用率
- **可视化图表** — 延迟曲线、丢包率柱状图、延迟 vs 丢包对比、网速趋势
- **告警提示** — 延迟/丢包/端口不可用自动标红提示
- **CSV 导出** — 一键下载历史数据
- **后台常驻** — 采集与 UI 分离，关闭面板不影响数据采集

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置目标
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入实际目标 IP/端口

# 3. 启动后台采集（常驻）
python daemon.py

# 4. 打开监控面板
streamlit run main.py
```

浏览器访问 `http://localhost:8501` 即可查看。

Windows 用户也可直接双击 `启动后台监控.bat` 和 `启动监控面板.bat`。

## 项目结构

```
proxy_monitor/
├── main.py              # Streamlit 仪表盘
├── daemon.py            # 后台采集守护进程
├── monitor.py           # 采集核心 (ping/tcp/http/speed)
├── stats.py             # 统计计算
├── view.py              # Plotly 图表
├── db.py                # SQLite 存储
├── config.example.yaml  # 配置模板
├── requirements.txt
└── .gitignore
```

## 配置说明

复制 `config.example.yaml` 为 `config.yaml`，修改以下字段：

```yaml
target:
  ip: 192.168.1.1        # 目标服务器 IP
  ports: [443, 8080]     # 要监测的 TCP 端口
  http_test_urls:        # HTTP 测试地址
    - http://192.168.1.1:8080/
monitor:
  interval: 10           # 采集间隔 (秒)
  speed_test_interval: 300  # 网速测试间隔 (秒)
alerts:
  latency_threshold_ms: 500
  packet_loss_threshold: 10
```

## 依赖

- Python ≥ 3.11 ,  Streamlit ,  Plotly ,  Pandas ,  Requests ,  PyYAML
