# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This repository contains the backend services for the Xiaozhi ESP32 AI assistant project. The system is composed of multiple components:

1. **xiaozhi-server** (Python) - Core AI processing backend
2. **manager-api** (Java/Spring Boot) - Management API backend
3. **manager-web** (Vue.js) - Web-based management interface
4. **manager-mobile** (Uni-app/Vue 3) - Mobile management interface

## Common Development Commands

### Python Backend (xiaozhi-server)
- Install dependencies: `pip install -r main/xiaozhi-server/requirements.txt`
- Run server: `cd main/xiaozhi-server && python app.py`
- Run with conda environment:
  ```
  conda create -n xiaozhi-esp32-server python=3.10
  conda activate xiaozhi-esp32-server
  conda install libopus ffmpeg
  pip install -r main/xiaozhi-server/requirements.txt
  python app.py
  ```

### Java Backend (manager-api)
- Build: `cd main/manager-api && mvn clean package`
- Run: `cd main/manager-api && mvn spring-boot:run`
- Or run the built JAR: `java -jar main/manager-api/target/xiaozhi-esp32-api.jar`

### Web Frontend (manager-web)
- Install dependencies: `cd main/manager-web && npm install`
- Development server: `cd main/manager-web && npm run serve`
- Build for production: `cd main/manager-web && npm run build`

### Mobile Frontend (manager-mobile)
- Install dependencies: `cd main/manager-mobile && pnpm install`
- Development server (H5): `cd main/manager-mobile && pnpm dev:h5`
- Build for production: `cd main/manager-mobile && pnpm build`

## Docker Deployment Commands

### Simple Deployment (Server only)
- `docker-compose -f main/xiaozhi-server/docker-compose.yml up -d`

### Full Deployment (All modules)
- `docker-compose -f main/xiaozhi-server/docker-compose_all.yml up -d`

## Architecture Overview

The system follows a microservices architecture:

1. **ESP32 Devices** communicate with the **Python Backend (xiaozhi-server)** via WebSocket
2. **Python Backend** connects to the **Java Backend (manager-api)** for configuration management
3. **Java Backend** provides REST APIs and manages data in MySQL/Redis
4. **Vue.js Web Interface** and **Uni-app Mobile Interface** connect to the Java Backend for management

Key directories:
- `main/xiaozhi-server/` - Python AI processing server
- `main/manager-api/` - Java Spring Boot management API
- `main/manager-web/` - Vue.js web management interface
- `main/manager-mobile/` - Uni-app mobile management interface
- `docs/` - Documentation and deployment guides

## Testing

### Python Server Testing
- Run individual tests: `cd main/xiaozhi-server && python -m pytest tests/`

### Java Backend Testing
- Run tests: `cd main/manager-api && mvn test`

## Configuration Files

Main configuration files:
- `main/xiaozhi-server/config.yaml` - Default server configuration
- `main/xiaozhi-server/config_from_api.yaml` - Configuration for connecting to manager-api
- `main/xiaozhi-server/data/.config.yaml` - Local override configuration (created by user)

Environment-specific configurations should be placed in the `data` directory as `.config.yaml`.