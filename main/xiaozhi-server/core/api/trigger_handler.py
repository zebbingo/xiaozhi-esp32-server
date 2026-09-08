# -*- coding: utf-8 -*-
"""
工位触发端点：外部事件（如放NFC卡）→ 让指定设备(Watcher)拍照识别 → 返回规范手办名。

用于"放卡写卡工位"（tools/figurine-capture-station）：读卡器检测到卡到位后
POST 本端点，由服务器主动调用设备 MCP 工具 self.camera.take_photo，
经 vision_handler 识别后把规范手办名返回给工位程序，由工位程序写卡。

本端点不碰串口、不写卡（串口由工位程序独占）。
"""

import json

from aiohttp import web

from config.logger import setup_logging
from core.providers.tools.device_mcp.mcp_handler import call_mcp_tool

TAG = __name__

DEFAULT_QUESTION = "这是什么？"


def _find_camera_tool(mcp_client):
    """在设备已注册的工具里找拍照工具（用 sanitized 注册名，has_tool 校验的就是它）。
    设备端工具名可能是 self_camera_take_photo 等，动态查找比写死更稳。"""
    tools = getattr(mcp_client, "tools", {}) or {}
    for cand in ("self_camera_take_photo", "take_photo"):
        if cand in tools:
            return cand
    for name in tools:
        low = name.lower()
        if "take_photo" in low or "takephoto" in low or "photo" in low or "camera" in low:
            return name
    return None


class TriggerHandler:
    def __init__(self, config: dict, ws_server):
        self.config = config
        self.ws_server = ws_server  # 用于在 active_connections 中按 device_id 找设备连接
        self.logger = setup_logging()

    def _find_conn(self, device_id: str):
        if not self.ws_server:
            return None
        for handler in list(self.ws_server.active_connections):
            if getattr(handler, "device_id", None) == device_id:
                return handler
        return None

    def _json(self, data: dict, status: int = 200):
        resp = web.Response(
            text=json.dumps(data, ensure_ascii=False, separators=(",", ":")),
            content_type="application/json",
            status=status,
        )
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Device-Id"
        return resp

    async def handle_options(self, request):
        return self._json({"ok": True})

    async def handle_post(self, request):
        try:
            try:
                body = await request.json()
            except Exception:
                body = {}
            device_id = (body.get("device_id")
                         or request.headers.get("Device-Id", "")).strip()
            question = body.get("question") or DEFAULT_QUESTION

            # 以下都是"正常业务结果"，统一返回 HTTP 200 + matched:false，
            # 便于机器客户端(工位app)直接读 JSON，而不是把它当成"服务不可达"。
            if not device_id:
                return self._json({"matched": False, "error": "缺少 device_id"})

            conn = self._find_conn(device_id)
            if conn is None:
                return self._json(
                    {"matched": False, "error": f"设备未在线或未连接: {device_id}"}
                )
            if not getattr(conn, "mcp_client", None):
                return self._json({"matched": False, "error": "设备MCP未就绪"})

            camera_tool = _find_camera_tool(conn.mcp_client)
            if not camera_tool:
                avail = list(getattr(conn.mcp_client, "tools", {}).keys())
                return self._json(
                    {"matched": False, "error": f"设备无拍照工具；可用工具: {avail}"}
                )

            self.logger.bind(tag=TAG).info(
                f"工位触发拍照识别：device={device_id} tool={camera_tool}"
            )
            # 主动让设备拍照；vision_handler 会识别并把结果作为工具返回值回传
            raw = await call_mcp_tool(
                conn, conn.mcp_client, camera_tool, json.dumps({"question": question})
            )

            # raw 是 vision_handler 的返回 JSON 字符串，如
            # {"success":true,"action":"RESPONSE","response":"这是t-rex","figurine":"t-rex"}
            figurine = None
            response_text = raw
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, dict):
                    figurine = parsed.get("figurine")
                    response_text = parsed.get("response", raw)
            except Exception:
                pass

            if figurine:
                return self._json({"matched": True, "name": figurine, "raw": response_text})
            return self._json({"matched": False, "name": None, "raw": response_text})

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"工位触发端点异常: {e}")
            return self._json({"matched": False, "error": str(e)}, status=500)
