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
        接收到 “shell” 命令后，将后续文本作为命令转发给 shell 容器执行，并将结果返回。
        该命令在私聊和群聊中都有效。
        """
        prefix = "shell"
        message_str = event.get_message_str()

        # 取出 /shell 之后的所有文本（包括换行），并做必要处理
        raw_command = message_str[len(prefix):]

        # 示例：去除每一行开头和结尾的空白，并过滤掉不可见控制字符
        # 如果不需要过滤控制字符，可删去相应的 re.sub
        lines = [line.strip() for line in raw_command.splitlines()]
        sanitized_command = "\n".join(lines)
        sanitized_command = re.sub(r'[\x00-\x1F\x7F]', '', sanitized_command)

        if not sanitized_command.strip():
            yield event.plain_result("未提供要执行的命令。")
            return

        logger.info(f"收到来自 {event.get_sender_name()} 的 Shell 命令: {sanitized_command}")

        target_url = "http://shell:5000/execute"
        try:
            # 通过 JSON 传递命令，默认会转义引号、换行等
            response = requests.post(target_url, json={"command": sanitized_command}, timeout=5)
            if response.ok:
                yield event.plain_result(response.text)
            else:
                yield event.plain_result(f"目标容器返回错误: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"请求目标容器失败: {e}")
            yield event.plain_result("无法连接目标容器。")

    async def terminate(self):
        """
        插件关闭或卸载前的收尾操作，暂不需要任何处理。
        """
        pass
