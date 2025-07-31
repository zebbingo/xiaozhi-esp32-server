from aiohttp import web
from config.logger import setup_logging
from core.auth import AuthMiddleware, AuthenticationError


class BaseHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.auth = AuthMiddleware(config)

    def _add_cors_headers(self, response):
        """添加CORS头信息"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Origin"] = "*"

    async def _auth_request(self, request):
        try:
            await self.auth.authenticate(request.headers)
        except AuthenticationError as e:
            self.logger.bind(tag=__name__).error(f"HTTP auth failed: {e}")
            raise web.HTTPUnauthorized(text="Unauthorized")
