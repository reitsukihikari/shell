from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import requests

@register("shell_plugin", "YourName", "Shell 命令执行插件", "1.0.0")
class ShellPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("shell")
    async def shell_command(self, event: AstrMessageEvent):
        """
        将 /shell 后的文本作为命令转发给 shell 容器执行，并反馈结果。
        """
        prefix = "/shell"
        message_str = event.message_str.strip()
        if not message_str.startswith(prefix):
            yield event.plain_result("命令格式错误，应以 /shell 开头。")
            return

        command = message_str[len(prefix):].strip()
        if not command:
            yield event.plain_result("未提供命令。")
            return

        logger.info(f"收到来自 {event.get_sender_name()} 的 shell 命令: {command}")

        # 目标容器地址，容器名为 "shell"
        target_url = "http://shell:5000/execute"
        try:
            response = requests.post(target_url, json={"command": command}, timeout=5)
            if response.ok:
                result_text = response.text
                yield event.plain_result(f"执行结果:\n{result_text}")
            else:
                yield event.plain_result(f"目标容器返回错误: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"请求目标容器失败: {e}")
            yield event.plain_result("无法连接目标容器。")

    async def terminate(self):
        pass
