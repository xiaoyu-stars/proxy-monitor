import os
import sys
import time
import atexit
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from monitor import MonitorThread
import db

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitor.pid')
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'monitor.log')

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


def write_pid():
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    try:
        os.remove(PID_FILE)
    except Exception:
        pass


def is_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        if pid == os.getpid():
            return False
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        remove_pid()
        return False


def main():
    if is_running():
        print("监控服务已在运行中")
        return

    log.info("=" * 40)
    log.info("监控服务启动")

    write_pid()
    atexit.register(remove_pid)

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    monitor = MonitorThread(config_path)
    monitor.start()

    print(f"后台监控已启动 (PID: {os.getpid()})")
    print(f"日志文件: {LOG_FILE}")
    print("关闭此窗口或按 Ctrl+C 可停止")
    log.info(f"监控线程已启动, 间隔 {monitor.config.interval}s")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        log.info("监控服务停止")
        print("\n正在停止...")
        monitor.stop()
        remove_pid()


if __name__ == '__main__':
    main()
