from aiohttp import web
import os
import json
from .base_handler import BaseHandler
from core.utils.data_privacy import (
    get_memory_file_path,
    get_log_file_path,
)

TAG = __name__


class DataPrivacyHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        self.gdpr_config = config.get("gdpr", {})

    def _features_enabled(self) -> bool:
        return self.gdpr_config.get("enabled", False)

    async def handle_get(self, request):
        if not self._features_enabled():
            return web.Response(status=403, text="GDPR features disabled")

        data = {}
        memory_path = get_memory_file_path(self.config)
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                data["memory"] = f.read()

        log_path = get_log_file_path(self.config)
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                data["logs"] = f.read()

        response = web.Response(
            text=json.dumps(data, ensure_ascii=False),
            content_type="application/json",
        )
        self._add_cors_headers(response)
        return response

    async def handle_delete(self, request):
        if not self._features_enabled():
            return web.Response(status=403, text="GDPR features disabled")

        memory_path = get_memory_file_path(self.config)
        log_path = get_log_file_path(self.config)
        if os.path.exists(memory_path):
            os.remove(memory_path)
        if os.path.exists(log_path):
            os.remove(log_path)

        response = web.Response(text="deleted")
        self._add_cors_headers(response)
        return response

    async def handle_put(self, request):
        if not self._features_enabled():
            return web.Response(status=403, text="GDPR features disabled")

        try:
            body = await request.text()
            memory_path = get_memory_file_path(self.config)
            with open(memory_path, "w", encoding="utf-8") as f:
                f.write(body)
            response = web.Response(text="updated")
        except Exception as e:
            response = web.Response(status=400, text=str(e))

        self._add_cors_headers(response)
        return response
