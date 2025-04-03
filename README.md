# shell_plugin

（已在 qq official webhook + linux 测试）

Shell 插件 命令：/shell xxx

其中 xxx 会发送到另一个目标容器执行 shell 命令。

由于官方 qq api 屏蔽链接或文件名，需要将目标容器的输出渲染成图像。

## 目标容器构建方式

```bash
- shell
  - app.py
  - Dockerfile
```

1. `app.py`

```py
import os
import pty
import subprocess
import select
import fcntl
import time
import uuid
from flask import Flask, request

app = Flask(__name__)

# 全局变量，管理伪终端和 bash 进程
master_fd, slave_fd, shell_process = None, None, None

def initialize_pty():
    global master_fd, slave_fd, shell_process
    master_fd, slave_fd = pty.openpty()
    shell_process = subprocess.Popen(
        ['/bin/bash'],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        universal_newlines=True,
        bufsize=0
    )
    fcntl.fcntl(master_fd, fcntl.F_SETFL, os.O_NONBLOCK)

def reinitialize_pty():
    global master_fd, slave_fd, shell_process
    try:
        shell_process.wait(timeout=2)
    except Exception:
        shell_process.terminate()
    try:
        os.close(master_fd)
    except Exception:
        pass
    try:
        os.close(slave_fd)
    except Exception:
        pass
    initialize_pty()

# 初始化伪终端
initialize_pty()

def flush_output(fd):
    """清空缓冲区，防止旧数据干扰新命令输出"""
    try:
        while True:
            data = os.read(fd, 1024)
            if not data:
                break
    except (BlockingIOError, OSError):
        pass

def read_command_output(fd, start_marker, end_marker, timeout=5):
    """
    循环读取直到检测到结束标记。
    按行解析输出，保留所有空行和空格，返回两标记之间文本。
    """
    output = ""
    end_time = time.time() + timeout
    while time.time() < end_time:
        r, _, _ = select.select([fd], [], [], 0.1)
        if r:
            try:
                data = os.read(fd, 1024)
                if data:
                    output += data.decode('utf-8', errors='ignore')
                    if end_marker in output:
                        break
            except OSError:
                break
    lines = output.splitlines()
    result_lines = []
    recording = False
    for line in lines:
        if start_marker in line:
            recording = True
            continue
        if end_marker in line and recording:
            recording = False
            break
        if recording:
            result_lines.append(line)
    return "\n".join(result_lines)

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json(force=True)
    command = data.get("command")
    if not command:
        return "未提供命令", 400

    flush_output(master_fd)

    uid = str(uuid.uuid4())
    start_marker = f"__CMD_BEGIN_{uid}__"
    end_marker = f"__CMD_END_{uid}__"

    os.write(master_fd, f"echo {start_marker}\n".encode())
    os.write(master_fd, (command + "\n").encode())
    os.write(master_fd, f"echo {end_marker}\n".encode())

    result = read_command_output(master_fd, start_marker, end_marker, timeout=5)

    if command.strip() == "exit":
        # exit 命令后重启伪终端
        reinitialize_pty()

    return result, 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
```

2. `Dockerfile`

```Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY app.py .
RUN pip install flask
EXPOSE 5001
CMD ["python", "app.py"]
```

执行

```bash
docker build -t shell .
docker run -d --name shell --network my_network -p 5001:5001 shell
```

其中 `my_network` 是和 webhook 的容器共享的网络。

# 支持

[帮助文档](https://astrbot.app)
