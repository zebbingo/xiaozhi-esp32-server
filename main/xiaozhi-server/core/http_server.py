import asyncio
import ssl
import time
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self._rate_limit_data = {}

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    def _check_rate_limit(self, ip: str) -> bool:
        cfg = self.config["server"].get("rate_limit", {})
        window = int(cfg.get("window_seconds", 60))
        max_req = int(cfg.get("max_requests", 60))
        now = time.time()
        start, count = self._rate_limit_data.get(ip, (now, 0))
        if now - start > window:
            self._rate_limit_data[ip] = (now, 1)
            return True
        if count >= max_req:
            return False
        self._rate_limit_data[ip] = (start, count + 1)
        return True

    @web.middleware
    async def _rate_limit_middleware(self, request, handler):
        peer = request.headers.get("X-Forwarded-For", request.remote)
        if not self._check_rate_limit(peer):
            self.logger.bind(tag=TAG).warning(f"Rate limit exceeded for {peer}")
            return web.Response(status=429, text="Too Many Requests")
        return await handler(request)

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            app = web.Application(middlewares=[self._rate_limit_middleware])

            read_config_from_api = server_config.get("read_config_from_api", False)

            if not read_config_from_api:
                # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                app.add_routes(
                    [
                        web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                        web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                        web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                    ]
                )
            # 添加路由
            app.add_routes(
                [
                    web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                ]
            )

            # 运行服务
            runner = web.AppRunner(app)
            await runner.setup()
            ssl_ctx = None
            ssl_conf = server_config.get("ssl", {})
            if ssl_conf.get("enabled"):
                try:
                    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    ssl_ctx.load_cert_chain(
                        ssl_conf.get("certfile", "server.crt"),
                        ssl_conf.get("keyfile", "server.key"),
                    )
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"加载SSL证书失败: {e}")

            site = web.TCPSite(runner, host, port, ssl_context=ssl_ctx)
            await site.start()

            # 保持服务运行
            while True:
                await asyncio.sleep(3600)  # 每隔 1 小时检查一次
