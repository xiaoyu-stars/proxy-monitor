import subprocess
import socket
import time
import threading
import re
import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- X-UI Traffic Client ----


class XuiClient:
    def __init__(self, panel_url, username, password):
        self.panel_url = panel_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})
        self._logged_in = False
        self._last_up = 0
        self._last_down = 0
        self._last_time = 0

    def _login(self):
        try:
            r = self.session.get(self.panel_url + '/', verify=False, timeout=10)
            csrf_match = re.search(r'csrf-token.*?content="(.*?)"', r.text)
            if csrf_match:
                self.session.headers["x-csrf-token"] = csrf_match.group(1)
            r2 = self.session.post(
                self.panel_url + '/login',
                json={"username": self.username, "password": self.password},
                verify=False, timeout=10
            )
            if r2.status_code == 200 and r2.json().get("success"):
                self._logged_in = True
                return True
        except Exception as e:
            pass
        return False

    def _get_traffic(self):
        if not self._logged_in and not self._login():
            return 0, 0
        try:
            r = self.session.get(
                self.panel_url + '/panel/api/inbounds/list',
                verify=False, timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    total_up = sum(o.get("up", 0) for o in data.get("obj", []))
                    total_down = sum(o.get("down", 0) for o in data.get("obj", []))
                    return total_up, total_down
            self._logged_in = False
        except Exception:
            self._logged_in = False
        return 0, 0

    def measure_speed(self):
        up_bytes, down_bytes = self._get_traffic()
        now = time.time()

        dl_speed = 0.0
        up_speed = 0.0

        if self._last_time > 0 and self._last_down > 0:
            elapsed = now - self._last_time
            if elapsed > 0:
                dl_delta = down_bytes - self._last_down
                up_delta = up_bytes - self._last_up
                dl_speed = (dl_delta * 8) / (elapsed * 1_000_000)
                up_speed = (up_delta * 8) / (elapsed * 1_000_000)

        self._last_up = up_bytes
        self._last_down = down_bytes
        self._last_time = now

        return round(max(dl_speed, 0), 2), round(max(up_speed, 0), 2)


# ---- Config ----

class Config:
    def __init__(self, path="config.yaml"):
        with open(path, 'r', encoding='utf-8') as f:
            self.data = yaml.safe_load(f)

    @property
    def target_ip(self):
        return self.data['target']['ip']

    @property
    def target_ports(self):
        return self.data['target']['ports']

    @property
    def http_urls(self):
        return self.data['target'].get('http_test_urls', [])

    @property
    def interval(self):
        return self.data['monitor']['interval']

    @property
    def ping_count(self):
        return self.data['monitor']['ping_count']

    @property
    def timeout(self):
        return self.data['monitor']['timeout']

    @property
    def speed_test_url(self):
        return self.data['monitor'].get('speed_test_url', '')

    @property
    def speed_test_interval(self):
        return self.data['monitor'].get('speed_test_interval', 300)

    @property
    def xui_enabled(self):
        return 'xui' in self.data

    @property
    def xui_panel_url(self):
        return self.data.get('xui', {}).get('panel_url', '')

    @property
    def xui_username(self):
        return self.data.get('xui', {}).get('username', '')

    @property
    def xui_password(self):
        return self.data.get('xui', {}).get('password', '')

    @property
    def xui_poll_interval(self):
        return self.data.get('xui', {}).get('traffic_poll_interval', 10)


def run_ping_test(ip, count=5, timeout=5):
    cmd = ['ping', '-n', str(count), '-w', str(timeout * 1000), ip]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * count + 5)
        output = result.stdout + result.stderr

        loss_match = re.search(r'(\d+)% loss|丢失 = (\d+)', output)
        loss_pct = 100.0
        if loss_match:
            val = loss_match.group(2) if loss_match.group(2) else loss_match.group(1)
            loss_pct = float(val)

        times = re.findall(r'time[=<](\d+)ms|时间[=<](\d+)ms', output)
        if times:
            times_ms = []
            for t in times:
                val = t[0] if t[0] else t[1]
                times_ms.append(float(val))
            avg = sum(times_ms) / len(times_ms)
            mn = min(times_ms)
            mx = max(times_ms)
            if len(times_ms) > 1:
                variance = sum((x - avg) ** 2 for x in times_ms) / len(times_ms)
                std = variance ** 0.5
            else:
                std = 0.0
            return avg, mn, mx, std, loss_pct

        return 0.0, 0.0, 0.0, 0.0, loss_pct
    except Exception:
        return 0.0, 0.0, 0.0, 0.0, 100.0


def run_tcp_test(ip, port, timeout=5):
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        elapsed = (time.time() - start) * 1000
        sock.close()
        return True, elapsed
    except Exception:
        return False, 0.0


def run_http_test(url, timeout=10):
    start = time.time()
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True, verify=False,
                          headers={'User-Agent': 'ProxyMonitor/1.0'})
        elapsed = (time.time() - start) * 1000
        return resp.status_code, elapsed, True
    except requests.exceptions.Timeout:
        return 0, timeout * 1000, False
    except Exception:
        return 0, 0.0, False


def run_speed_test(url, timeout=15):
    start = time.time()
    try:
        resp = requests.get(url, timeout=timeout, stream=True, verify=False,
                          headers={'User-Agent': 'ProxyMonitor/1.0'})
        bytes_downloaded = 0
        for chunk in resp.iter_content(chunk_size=32768):
            bytes_downloaded += len(chunk)
            if time.time() - start > timeout:
                break
        elapsed = time.time() - start
        if elapsed > 0 and bytes_downloaded > 0:
            speed_mbps = (bytes_downloaded * 8) / (elapsed * 1_000_000)
            return round(speed_mbps, 2)
        return 0.0
    except Exception:
        return 0.0


def run_upload_test(url, timeout=10):
    test_data = b'\x00' * (256 * 1024)
    start = time.time()
    try:
        resp = requests.post(url, data=test_data, timeout=timeout, verify=False,
                           headers={'User-Agent': 'ProxyMonitor/1.0'})
        elapsed = time.time() - start
        if elapsed > 0:
            speed_mbps = (len(test_data) * 8) / (elapsed * 1_000_000)
            return round(speed_mbps, 2)
        return 0.0
    except Exception:
        return 0.0


class MonitorThread(threading.Thread):
    def __init__(self, config_path="config.yaml"):
        super().__init__(daemon=True)
        self.config = Config(config_path)
        self._running = False
        self._db_module = None
        self._last_speed_test = 0
        self._xui_client = None

    def run(self):
        import db
        self._db_module = db
        db.init_db()

        if self.config.xui_enabled:
            self._xui_client = XuiClient(
                self.config.xui_panel_url,
                self.config.xui_username,
                self.config.xui_password
            )

        self._running = True
        while self._running:
            try:
                self._run_cycle()
            except Exception as e:
                print(f"Monitor error: {e}")
            for _ in range(int(self.config.interval)):
                if not self._running:
                    break
                time.sleep(1)

    def _run_cycle(self):
        db = self._db_module
        cfg = self.config

        avg_ms, min_ms, max_ms, std_dev, loss_pct = run_ping_test(
            cfg.target_ip, cfg.ping_count, cfg.timeout
        )
        db.insert_ping(avg_ms, min_ms, max_ms, std_dev, loss_pct)

        for port in cfg.target_ports:
            connected, connect_time = run_tcp_test(cfg.target_ip, port, cfg.timeout)
            db.insert_tcp(port, 1 if connected else 0, connect_time)

        for url in cfg.http_urls:
            status_code, elapsed, success = run_http_test(url, cfg.timeout)
            db.insert_http(url, status_code, elapsed, success)

        now = time.time()
        if self._xui_client and now - self._last_speed_test >= cfg.xui_poll_interval:
            dl_speed, up_speed = self._xui_client.measure_speed()
            if dl_speed > 0 or up_speed > 0:
                db.insert_speed(dl_speed, up_speed)
            self._last_speed_test = now

    def stop(self):
        self._running = False
