import re
import requests
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.core.star.filter.event_message_type import EventMessageType

@register("shell_plugin", "reika", "Shell 命令执行插件", "1.0.0")
class ShellPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("shell", event_message_type=EventMessageType.ALL)
    async def shell_command(self, event: AstrMessageEvent):
        """
        接收到 “shell” 命令后，将后续文本作为命令转发给 shell 容器执行，
        将结果返回，并写入当前目录 log 文件（不存在则创建）。
        """
        prefix = "shell"
        message_str = event.get_message_str()
        raw_command = message_str[len(prefix):]
        lines = [line.strip() for line in raw_command.splitlines()]
        sanitized_command = "\n".join(lines)
        sanitized_command = re.sub(r'[\x00-\x1F\x7F]', '', sanitized_command)

        if not sanitized_command.strip():
            yield event.plain_result("未提供要执行的命令。")
            return

        logger.info(f"收到来自 {event.get_sender_name()} 的 Shell 命令: {sanitized_command}")

        target_url = "http://shell:5000/execute"
        try:
            response = requests.post(target_url, json={"command": sanitized_command}, timeout=5)
            if response.ok:
                result_text = response.text
                yield event.plain_result(result_text)
            else:
                result_text = f"目标容器返回错误: {response.status_code}"
                yield event.plain_result(result_text)
        except requests.RequestException as e:
            logger.error(f"请求目标容器失败: {e}")
            result_text = "无法连接目标容器。"
            yield event.plain_result(result_text)

        try:
            with open("log", "a", encoding="utf-8") as f:
                f.write(result_text + "\n")
        except Exception as log_e:
            logger.error(f"写入 log 文件失败: {log_e}")

    async def terminate(self):
        pass
