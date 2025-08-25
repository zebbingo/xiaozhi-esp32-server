# Server API Interaction Documentation

This document describes the interaction between the xiaozhi-server (Python backend) and manager-api (Java backend) through RESTful API endpoints.

## Overview

The xiaozhi-server communicates with the manager-api to exchange configuration data, report chat history, and manage agent memories. This interaction enables centralized management of the AI assistant system through the web interface.

## Authentication

All requests from xiaozhi-server to manager-api are authenticated using a Bearer token in the Authorization header:
- The token is configured in the `config_from_api.yaml` file as the `secret` parameter
- The manager-api validates this token to ensure only authorized xiaozhi-server instances can communicate with it

## API Endpoints

### Configuration Endpoints

#### POST /config/server-base
- **Purpose**: Get server base configuration
- **Usage**: Called by xiaozhi-server to retrieve general server configuration parameters

#### POST /config/agent-models
- **Purpose**: Get agent model configurations
- **Usage**: Called by xiaozhi-server to retrieve model configurations for specific agents
- **Parameters**: 
  - macAddress: Device MAC address
  - selectedModule: Selected module configuration
  - clientId: Client identifier

### Agent Management Endpoints

#### PUT /agent/saveMemory/{macAddress}
- **Purpose**: Save agent memory based on device MAC address
- **Usage**: xiaozhi-server periodically saves agent memory summaries to manager-api
- **Parameters**: 
  - macAddress: Device MAC address (path parameter)
  - summaryMemory: Memory summary content (JSON body)
- **Benefits**: Allows the web interface to display current agent memory states

#### POST /agent/chat-history/report
- **Purpose**: Report chat history with audio data
- **Usage**: xiaozhi-server reports chat interactions to manager-api
- **Parameters**:
  - macAddress: Device MAC address
  - sessionId: Chat session identifier
  - chatType: Type of chat interaction
  - content: Chat content text
  - reportTime: Timestamp of the interaction
  - audioBase64: Base64 encoded audio data (optional)
- **Benefits**: Enables the web interface to display chat history and play audio responses

## Error Handling

The interaction implements robust error handling:
- Retry logic for network-related failures in the manage_api_client.py
- Specific exceptions for device not found and device binding errors
- HTTP status code and API response code validation to handle business logic errors

## Implementation Details

The communication is implemented in `main/xiaozhi-server/config/manage_api_client.py` which provides:
- Singleton pattern for the API client
- Persistent HTTP connection pool
- Retry mechanism with exponential backoff
- Automatic error detection and handling
- Proper resource cleanup

## Data Flow

1. **Startup**: xiaozhi-server retrieves configuration from manager-api
2. **Runtime**: Periodic memory state synchronization
3. **Interaction**: Real-time chat history reporting with optional audio
4. **Management**: Web interface accesses data through manager-api

This architecture allows the xiaozhi-server to operate independently while still synchronizing important data with the manager-api for centralized management through the web interface.