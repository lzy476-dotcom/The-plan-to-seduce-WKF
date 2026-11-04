"""一键启动脚本。

用法：在本目录下运行
    python start.py

作用：启动 FastAPI 后端（Uvicorn），并自动打开浏览器访问页面。
手机在同一个 WiFi 下，用 http://<电脑IP>:8000 也能访问。
"""
import os
import sys
import threading
import webbrowser

import uvicorn


def main() -> None:
    # 确保以 backend 为工作目录，这样 main.py 里的「前端目录」等相对路径才能正确解析
    backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    os.chdir(backend_dir)
    # 把 backend 加进模块搜索路径，让 uvicorn 能 import 到 main
    sys.path.insert(0, backend_dir)

    host = "0.0.0.0"
    port = 8000
    url = f"http://127.0.0.1:{port}"

    print("=" * 40)
    print("  饮食记录 · 后端启动中……")
    print(f"  本机访问：{url}")
    print("  手机访问：连同一 WiFi，浏览器打开 http://<电脑IP>:8000")
    print("  按 Ctrl+C 停止")
    print("=" * 40)

    # 稍等片刻自动打开浏览器
    def _open_browser() -> None:
        webbrowser.open(url)

    threading.Timer(1.5, _open_browser).start()

    uvicorn.run("main:app", host=host, port=port)


if __name__ == "__main__":
    main()
