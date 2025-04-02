import requests
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.core.star.filter.event_message_type import EventMessageType


@register("shell_plugin", "YourName", "Shell 命令执行插件", "1.0.0")
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
        message_str = event.get_message_str().strip()
        if not message_str.startswith(prefix):
            yield event.plain_result("命令格式错误，应以 /shell 开头。")
            return

        # 截取真正的命令内容
        command = message_str[len(prefix):].strip()
        if not command:
            yield event.plain_result("未提供要执行的命令。")
            return

        logger.info(f"收到来自 {event.get_sender_name()} 的 Shell 命令: {command}")

        target_url = "http://shell:5000/execute"
        try:
            response = requests.post(target_url, json={"command": command}, timeout=5)
            if response.ok:
                # 直接返回目标容器的结果
                result_text = response.text
                yield event.plain_result(result_text)
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
