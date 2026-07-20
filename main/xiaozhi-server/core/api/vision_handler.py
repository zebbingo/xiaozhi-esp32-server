import json
import copy
import os
from aiohttp import web
import aiohttp
from config.logger import setup_logging
from core.api.base_handler import BaseHandler
from core.utils.util import get_vision_url, is_valid_image_file
from core.utils.vllm import create_instance
from config.config_loader import get_private_config_from_api
from core.utils.auth import AuthToken
import base64
from typing import Tuple, Optional
from plugins_func.register import Action

TAG = __name__

# 设置最大文件大小为5MB
MAX_FILE_SIZE = 5 * 1024 * 1024

# 手办识别微服务地址（tools/figurine-recognizer），留空则跳过识别直接走VLLM
FIGURINE_RECOGNIZER_URL = os.getenv("FIGURINE_RECOGNIZER_URL", "").strip()

# 手办 NFC 写卡服务地址（tools/figurine-nfc-writer，主机原生运行）。
# 留空则不写卡。容器内访问主机用 http://host.docker.internal:8005/write
FIGURINE_NFC_WRITER_URL = os.getenv("FIGURINE_NFC_WRITER_URL", "").strip()

# 调试用：把设备实拍的照片存到 data/vision_captures/，用于采集设备参考图
SAVE_VISION_CAPTURES = os.getenv("SAVE_VISION_CAPTURES", "").strip() == "1"
VISION_CAPTURE_DIR = "/opt/xiaozhi-esp32-server/data/vision_captures"


def _save_capture(logger, image_data: bytes) -> None:
    """把设备实拍照片落盘（仅调试采集时开启）。"""
    if not SAVE_VISION_CAPTURES:
        return
    try:
        import time

        os.makedirs(VISION_CAPTURE_DIR, exist_ok=True)
        # 毫秒时间戳命名，保证唯一
        fname = f"capture_{int(time.time() * 1000)}.jpg"
        with open(os.path.join(VISION_CAPTURE_DIR, fname), "wb") as f:
            f.write(image_data)
        logger.bind(tag=TAG).info(f"已保存设备实拍照片：{fname}")
    except Exception as e:
        logger.bind(tag=TAG).warning(f"保存设备照片失败：{e}")


async def _recognize_figurine(logger, image_data: bytes) -> Optional[str]:
    """把图片发给本地手办识别服务，识别到就返回手办名，否则返回 None。"""
    if not FIGURINE_RECOGNIZER_URL:
        return None
    try:
        form = aiohttp.FormData()
        form.add_field(
            "file", image_data, filename="capture.jpg", content_type="image/jpeg"
        )
        timeout = aiohttp.ClientTimeout(total=8)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(FIGURINE_RECOGNIZER_URL, data=form) as resp:
                if resp.status != 200:
                    logger.bind(tag=TAG).warning(
                        f"手办识别服务返回状态码 {resp.status}"
                    )
                    return None
                result = await resp.json()
        if result.get("matched"):
            return result.get("name")
        return None
    except Exception as e:
        # 识别服务不可用不应影响正常视觉问答，降级为不注入
        logger.bind(tag=TAG).warning(f"调用手办识别服务失败，跳过：{e}")
        return None


async def _write_figurine_nfc(logger, name: str) -> None:
    """识别命中后，通知主机侧 NFC 写卡服务向公仔卡写入角色名。
    写卡失败不应影响语音播报，只记日志（降级）。"""
    if not FIGURINE_NFC_WRITER_URL:
        return
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(FIGURINE_NFC_WRITER_URL, json={"name": name}) as resp:
                result = await resp.json()
        if result.get("ok"):
            logger.bind(tag=TAG).info(
                f"NFC 写卡成功：{name} -> 角色名 {result.get('role')} "
                f"(UID {result.get('uid')}, 块 {result.get('written_blocks')})"
            )
        else:
            logger.bind(tag=TAG).warning(
                f"NFC 写卡未成功：{name}，原因：{result.get('error')}"
            )
    except Exception as e:
        # 写卡服务不可用（如没插读卡器/服务没起）不应影响语音，降级
        logger.bind(tag=TAG).warning(f"调用 NFC 写卡服务失败，跳过：{e}")


class VisionHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        # 初始化认证工具
        self.auth = AuthToken(config["server"]["auth_key"])

    def _create_error_response(self, message: str) -> dict:
        """创建统一的错误响应格式"""
        return {"success": False, "message": message}

    def _verify_auth_token(self, request) -> Tuple[bool, Optional[str]]:
        """验证认证token"""
        # 测试模式：允许特定测试令牌或跳过验证
        auth_header = request.headers.get("Authorization", "")
        client_id = request.headers.get("Client-Id", "")

        # 允许测试客户端跳过认证
        if client_id == "web_test_client":
            device_id = request.headers.get("Device-Id", "test_device")
            return True, device_id

        if not auth_header.startswith("Bearer "):
            return False, None

        token = auth_header[7:]  # 移除"Bearer "前缀
        return self.auth.verify_token(token)

    async def handle_post(self, request):
        """处理 MCP Vision POST 请求"""
        response = None  # 初始化response变量
        try:
            # 验证token
            is_valid, token_device_id = self._verify_auth_token(request)
            if not is_valid:
                response = web.Response(
                    text=json.dumps(
                        self._create_error_response("无效的认证token或token已过期")
                    ),
                    content_type="application/json",
                    status=401,
                )
                return response

            # 获取请求头信息
            device_id = request.headers.get("Device-Id", "")
            client_id = request.headers.get("Client-Id", "")
            if device_id != token_device_id:
                raise ValueError("设备ID与token不匹配")
            # 解析multipart/form-data请求
            reader = await request.multipart()

            # 读取question字段
            question_field = await reader.next()
            if question_field is None:
                raise ValueError("缺少问题字段")
            question = await question_field.text()
            self.logger.bind(tag=TAG).debug(f"Question: {question}")

            # 读取图片文件
            image_field = await reader.next()
            if image_field is None:
                raise ValueError("缺少图片文件")

            # 读取图片数据
            image_data = await image_field.read()
            if not image_data:
                raise ValueError("图片数据为空")

            # 检查文件大小
            if len(image_data) > MAX_FILE_SIZE:
                raise ValueError(
                    f"图片大小超过限制，最大允许{MAX_FILE_SIZE/1024/1024}MB"
                )

            # 检查文件格式
            if not is_valid_image_file(image_data):
                raise ValueError(
                    "不支持的文件格式，请上传有效的图片文件（支持JPEG、PNG、GIF、BMP、TIFF、WEBP格式）"
                )

            # 调试采集：把设备实拍照片存下来，用于生成设备参考图
            _save_capture(self.logger, image_data)

            # 先经过本地手办识别服务
            figurine_name = await _recognize_figurine(self.logger, image_data)

            if figurine_name:
                # 识别命中：直接返回简短结果，不再调用 VLLM 长篇描述
                self.logger.bind(tag=TAG).info(f"手办识别命中：{figurine_name}")
                # 识别命中后触发向公仔 NFC 卡写入角色名（失败不阻塞语音播报）
                await _write_figurine_nfc(self.logger, figurine_name)
                # 播报名用空格替换下划线（如 julius_caesar → julius caesar）
                display_name = figurine_name.replace("_", " ")
                result = f"这是{display_name}"
            else:
                # 未识别到已知手办：退回 VLLM 做视觉描述
                image_base64 = base64.b64encode(image_data).decode("utf-8")

                # 如果开启了智控台，则从智控台获取模型配置
                current_config = copy.deepcopy(self.config)
                read_config_from_api = current_config.get(
                    "read_config_from_api", False
                )
                if read_config_from_api:
                    current_config = await get_private_config_from_api(
                        current_config,
                        device_id,
                        client_id,
                    )

                select_vllm_module = current_config["selected_module"].get("VLLM")
                if not select_vllm_module:
                    raise ValueError("您还未设置默认的视觉分析模块")

                vllm_type = (
                    select_vllm_module
                    if "type" not in current_config["VLLM"][select_vllm_module]
                    else current_config["VLLM"][select_vllm_module]["type"]
                )

                if not vllm_type:
                    raise ValueError(f"无法找到VLLM模块对应的供应器{vllm_type}")

                vllm = create_instance(
                    vllm_type, current_config["VLLM"][select_vllm_module]
                )

                result = vllm.response(question, image_base64)

            return_json = {
                "success": True,
                "action": Action.RESPONSE.name,
                "response": result,
                # 识别命中的规范手办名（带下划线，如 julius_caesar）；未命中为 None。
                # 供工位触发端点(/mcp/vision/trigger)提取规范名用，语音流程忽略此字段。
                "figurine": figurine_name,
            }

            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except ValueError as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POST请求异常: {e}")
            return_json = self._create_error_response(str(e))
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POST请求异常: {e}")
            return_json = self._create_error_response("处理请求时发生错误")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            if response:
                self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """处理 MCP Vision GET 请求"""
        try:
            vision_explain = get_vision_url(self.config)
            if vision_explain and len(vision_explain) > 0 and "null" != vision_explain:
                message = (
                    f"MCP Vision 接口运行正常，视觉解释接口地址是：{vision_explain}"
                )
            else:
                message = "MCP Vision 接口运行不正常，请打开data目录下的.config.yaml文件，找到【server.vision_explain】，设置好地址"

            response = web.Response(text=message, content_type="text/plain")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision GET请求异常: {e}")
            return_json = self._create_error_response("服务器内部错误")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response
