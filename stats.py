import statistics
import math
from db import query_ping, query_tcp, query_http, query_speed, query_latest_ping, query_latest_tcp, query_latest_http, query_latest_speed


def calc_ping_stats(hours=24):
    rows = query_ping(hours)
    if not rows:
        return {
            'avg': 0, 'median': 0, 'min': 0, 'max': 0,
            'std_dev': 0, 'loss_pct': 100, 'jitter': 0,
            'sample_count': 0
        }

    avg_vals = [r[1] for r in rows if r[1] > 0]
    loss_vals = [r[5] for r in rows]
    min_vals = [r[2] for r in rows if r[2] > 0]
    max_vals = [r[3] for r in rows if r[3] > 0]

    if not avg_vals:
        return {
            'avg': 0, 'median': 0, 'min': 0, 'max': 0,
            'std_dev': 0, 'loss_pct': 100, 'jitter': 0,
            'sample_count': len(rows)
        }

    avg = statistics.mean(avg_vals)
    med = statistics.median(avg_vals)
    mn = min(min_vals) if min_vals else 0
    mx = max(max_vals) if max_vals else 0
    std = statistics.stdev(avg_vals) if len(avg_vals) > 1 else 0

    diffs = [abs(avg_vals[i] - avg_vals[i-1]) for i in range(1, len(avg_vals))]
    jitter = statistics.mean(diffs) if diffs else 0

    avg_loss = statistics.mean(loss_vals) if loss_vals else 0

    return {
        'avg': round(avg, 1),
        'median': round(med, 1),
        'min': round(mn, 1),
        'max': round(mx, 1),
        'std_dev': round(std, 1),
        'loss_pct': round(avg_loss, 1),
        'jitter': round(jitter, 1),
        'sample_count': len(rows)
    }


def calc_tcp_stats(hours=24):
    rows = query_tcp(hours)
    if not rows:
        ports_stats = {}
    else:
        ports_stats = {}
        for r in rows:
            port = r[1]
            if port not in ports_stats:
                ports_stats[port] = {'connected': 0, 'total': 0, 'times': []}
            ports_stats[port]['total'] += 1
            if r[2]:
                ports_stats[port]['connected'] += 1
                if r[3] > 0:
                    ports_stats[port]['times'].append(r[3])

    result = {}
    for port, data in ports_stats.items():
        total = data['total']
        success = data['connected']
        availability = round(success / total * 100, 1) if total > 0 else 0
        avg_time = round(statistics.mean(data['times']), 1) if data['times'] else 0
        result[port] = {
            'availability': availability,
            'avg_connect_time_ms': avg_time,
            'total_tests': total
        }
    return result


def calc_http_stats(hours=24):
    rows = query_http(hours)
    if not rows:
        return {}

    url_stats = {}
    for r in rows:
        url = r[1]
        if url not in url_stats:
            url_stats[url] = {'success': 0, 'total': 0, 'times': []}
        url_stats[url]['total'] += 1
        if r[4]:
            url_stats[url]['success'] += 1
            if r[3] > 0:
                url_stats[url]['times'].append(r[3])

    result = {}
    for url, data in url_stats.items():
        total = data['total']
        success = data['success']
        availability = round(success / total * 100, 1) if total > 0 else 0
        avg_time = round(statistics.mean(data['times']), 1) if data['times'] else 0
        max_time = round(max(data['times']), 1) if data['times'] else 0
        short_url = url.split('//')[-1].split('/')[0] if '//' in url else url
        result[short_url] = {
            'availability': availability,
            'avg_response_ms': avg_time,
            'max_response_ms': max_time,
            'total_tests': total
        }
    return result


def get_latest_status():
    ping = query_latest_ping()
    tcp = query_latest_tcp()
    http = query_latest_http()
    speed = query_latest_speed()

    status = {
        'ping': None,
        'tcp': [],
        'http': [],
        'speed': None
    }

    if ping:
        status['ping'] = {
            'timestamp': ping[0],
            'avg_ms': round(ping[1], 1),
            'loss_pct': round(ping[5], 1)
        }

    for r in tcp:
        status['tcp'].append({
            'port': r[0],
            'connected': bool(r[1]),
            'connect_time_ms': round(r[2], 1)
        })

    for r in http:
        short_url = r[0].split('//')[-1].split('/')[0] if '//' in r[0] else r[0]
        status['http'].append({
            'url': short_url,
            'status_code': r[1],
            'response_ms': round(r[2], 1),
            'success': bool(r[3])
        })

    if speed:
        status['speed'] = {
            'timestamp': speed[0],
            'download_mbps': round(speed[1], 2)
        }

    return status


def get_ping_dataframe(hours=24):
    rows = query_ping(hours)
    import pandas as pd
    if not rows:
        return pd.DataFrame(columns=['timestamp', 'avg_ms', 'min_ms', 'max_ms', 'std_dev', 'loss_pct'])
    df = pd.DataFrame(rows, columns=['timestamp', 'avg_ms', 'min_ms', 'max_ms', 'std_dev', 'loss_pct'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def calc_speed_stats(hours=24):
    rows = query_speed(hours)
    if not rows:
        return {'avg_dl': 0, 'max_dl': 0, 'min_dl': 0, 'sample_count': 0}

    dl_vals = [r[1] for r in rows if r[1] > 0]
    if not dl_vals:
        return {'avg_dl': 0, 'max_dl': 0, 'min_dl': 0, 'sample_count': len(rows)}

    return {
        'avg_dl': round(statistics.mean(dl_vals), 2),
        'max_dl': round(max(dl_vals), 2),
        'min_dl': round(min(dl_vals), 2),
        'sample_count': len(rows)
    }


def get_speed_dataframe(hours=24):
    rows = query_speed(hours)
    import pandas as pd
    if not rows:
        return pd.DataFrame(columns=['timestamp', 'download_mbps', 'upload_mbps'])
    df = pd.DataFrame(rows, columns=['timestamp', 'download_mbps', 'upload_mbps'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def get_tcp_dataframe(hours=24):
    rows = query_tcp(hours)
    import pandas as pd
    if not rows:
        return pd.DataFrame(columns=['timestamp', 'port', 'connected', 'connect_time_ms'])
    df = pd.DataFrame(rows, columns=['timestamp', 'port', 'connected', 'connect_time_ms'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df
