import os
import time
from config.config_loader import get_project_dir


def get_memory_file_path(config: dict) -> str:
    return get_project_dir() + "data/.memory.yaml"


def get_log_file_path(config: dict) -> str:
    log_dir = config.get("log", {}).get("log_dir", "tmp")
    log_file = config.get("log", {}).get("log_file", "server.log")
    return os.path.join(get_project_dir(), log_dir, log_file)


def purge_expired_data(config: dict):
    gdpr_cfg = config.get("gdpr", {})
    days = int(gdpr_cfg.get("retention_days", 0))
    if days <= 0:
        return
    expire_seconds = days * 86400
    now = time.time()
    for path in [get_memory_file_path(config), get_log_file_path(config)]:
        if os.path.exists(path) and now - os.path.getmtime(path) > expire_seconds:
            try:
                os.remove(path)
            except OSError:
                pass
