### Product Requirements Document: Xiaozhi-ESP32-Server (Brownfield Project)

### 1. Introduction

This document outlines the product requirements for the Xiaozhi-ESP32-Server, a project aimed at creating a "low-cost civilian Jarvis solution" with the capability for "intelligent linkage of peripheral hardware". This is a brownfield project that will build upon the existing codebase of the Xiaozhi-ESP32-Server.

**1.1 Project Goal**

The primary goal of this project is to develop an open-source, low-cost, and extensible personal AI assistant that can be deployed by individuals and developers. The project aims to replicate and build upon the functionalities of advanced AI assistants, making them accessible to a wider audience. The key objectives are:

* **To provide a low-cost alternative to commercial AI assistants.**
* **To enable intelligent control and interaction with IoT devices.**
* **To foster a community of developers who can contribute to the project and expand its capabilities.**

**1.2 Target Audience**

The target audience for the Xiaozhi-ESP32-Server includes:

* **AI Enthusiasts and Hobbyists:** Individuals interested in exploring and experimenting with AI and IoT technologies.
* **Developers:** Programmers who want to build custom AI applications and integrate them with hardware.
* **DIY Community:** Makers and tinkerers who want to build their own smart home devices and personal assistants.

### 2. Product Features

The Xiaozhi-ESP32-Server will have the following core features:

**2.1 Core Architecture**

* The system is built on a robust core architecture that utilizes WebSocket and HTTP servers to provide a comprehensive management console and a secure authentication system.

**2.2 Voice Interaction**

* **Streaming ASR (Automatic Speech Recognition):** The system supports real-time, streaming speech recognition.
* **Streaming TTS (Text-to-Speech):** It provides streaming text-to-speech synthesis for natural-sounding voice responses.
* **VAD (Voice Activity Detection):** The system can detect voice activity to start and stop recording automatically.
* **Multi-language Support:** It supports speech recognition and synthesis in multiple languages.

**2.3 Voiceprint Recognition**

* The server supports multi-user voiceprint registration, management, and recognition.
* It can identify the speaker in real-time and provide personalized responses through the Large Language Model (LLM).

**2.4 Intelligent Conversation**

* The system supports a variety of LLMs to facilitate intelligent and natural conversations.

**2.5 Visual Perception**

* The server is capable of multi-modal interaction through the support of multiple Vision Large Language Models (VLLMs).

**2.6 Extensibility**

* **Plugin System:** The server has a plugin-based architecture that allows for easy extension of its functionalities, such as adding support for weather forecasts, news updates, music playback, and more.
* **IoT Integration:** The system is designed to control and interact with various IoT devices.

### 3. User Personas

**3.1 Alex - The AI Enthusiast**

* **Description:** Alex is a tech-savvy individual who is passionate about AI and home automation. He enjoys tinkering with new technologies and wants to build his own personal AI assistant.
* **Goals:**
    * To have a personal assistant that can control his smart home devices.
    * To experiment with different AI models and customize the assistant's personality.
    * To contribute to an open-source AI project.

**3.2. Sarah - The Developer**

* **Description:** Sarah is a software developer with experience in Python and web technologies. She is interested in building custom AI applications for her clients.
* **Goals:**
    * To use the Xiaozhi-ESP32-Server as a platform for developing custom AI solutions.
    * To integrate the server with other systems and services.
    * To contribute to the development of the core functionalities of the server.

### 4. Technical Requirements

**4.1 Technology Stack**

* **Backend:** Python 3.10, Java 21, Spring Boot
* **Frontend:** Vue.js, Node.js 18
* **Database:** MySQL, Redis
* **Deployment:** Docker

**4.2 System Requirements**

* The server should be deployable on a low-cost hardware platform, such as a Raspberry Pi or a small server.
* The system should be designed to be scalable and support a growing number of users and devices.

### 5. System Architecture

The Xiaozhi-ESP32-Server consists of the following main components:

* **xiaozhi-server:** The core Python server that handles WebSocket connections, AI processing (ASR, TTS, LLM), and communication with IoT devices.
* **manager-web:** A web-based management interface built with Vue.js that allows users to configure the system, manage users and devices, and monitor the server's status.
* **manager-api:** A Java-based REST API that provides the backend services for the `manager-web` interface.
* **ESP32 Client:** The firmware for the ESP32 devices that enables them to connect to the server and interact with the AI assistant.

### 6. Future Enhancements

Based on the project's open letter to contributors and the issue templates, the following are potential areas for future development:

* **Improved AI Models:** Integration of more advanced and efficient ASR, TTS, and LLM models.
* **Expanded Plugin Library:** Development of a wider range of plugins to support more services and devices.
* **Mobile Application:** Creation of a mobile application for interacting with the AI assistant.
* **Enhanced Security:** Implementation of more robust security features to protect user data and privacy.
* **Community-driven Development:** Fostering an active community of developers to contribute to the project and drive its future direction.