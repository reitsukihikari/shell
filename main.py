import re
import requests
import io
from PIL import Image, ImageDraw, ImageFont
from astrbot.api import logger
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.core.star.filter.event_message_type import EventMessageType

def text_to_image(text, font_path=None, font_size=14):
    font = ImageFont.load_default() if not font_path else ImageFont.truetype(font_path, font_size)
    lines = text.splitlines() or ['']
    dummy_img = Image.new('RGB', (1, 1))
    dummy_draw = ImageDraw.Draw(dummy_img)
    max_width = 0
    line_heights = []
    for line in lines:
        bbox = dummy_draw.textbbox((0, 0), line, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        max_width = max(max_width, width)
        line_heights.append(height)
    line_height = max(line_heights)
    img_width = max_width + 20
    img_height = line_height * len(lines) + 20
    img = Image.new('RGB', (img_width, img_height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    y_text = 10
    for line in lines:
        draw.text((10, y_text), line, font=font, fill=(0, 0, 0))
        y_text += line_height
    output = io.BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output

@register("shell_plugin", "reika", "Shell 命令执行插件", "1.0.0")
class ShellPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    @filter.command("shell", event_message_type=EventMessageType.ALL)
    async def shell_command(self, event: AstrMessageEvent):
        """
        接收到 “shell” 命令后，将后续文本作为命令转发给 shell 容器执行，
        将结果以图片形式返回，并写入当前目录 log 文件（不存在则创建）。
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

        target_url = "http://shell:5001/execute"
        try:
            response = requests.post(target_url, json={"command": sanitized_command}, timeout=5)
            if response.ok:
                result_text = response.text
            else:
                result_text = f"目标容器返回错误: {response.status_code}"
        except requests.RequestException as e:
            logger.error(f"请求目标容器失败: {e}")
            result_text = "无法连接目标容器。"

        # 将结果文本转换为图片
        image_bytes = text_to_image(result_text)
        # 发送图片（需根据具体 API 调用适配图片消息发送方式）
        yield event.image_result(image_bytes)

        try:
            with open("log", "a", encoding="utf-8") as f:
                f.write(result_text + "\n")
        except Exception as log_e:
            logger.error(f"写入 log 文件失败: {log_e}")

    async def terminate(self):
        pass
