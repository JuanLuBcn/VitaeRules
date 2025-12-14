# Running VitaeRules on Raspberry Pi 5

This guide explains how to deploy the VitaeRules bot on a Raspberry Pi 5, which is powerful enough to run the application and a small local LLM (via Ollama).

## Prerequisites

1.  **Raspberry Pi 5** (4GB or 8GB RAM recommended).
2.  **Docker & Docker Compose** installed.
3.  **Ollama** installed and running (either natively or in another container).

## Important Note for Home Assistant Users

If you are running this from the **Home Assistant "Advanced SSH & Web Terminal"**, you are in a "Docker-outside-of-Docker" environment. This means:
1.  You can run `docker` commands.
2.  **BUT** the Docker daemon (on the host) cannot see your files (inside the container) via normal paths.

**We have updated the configuration to handle this:**
*   **Data**: Uses a "Named Volume" (`vitae_data`) instead of a local folder. This ensures your database persists safely on the host.
*   **Config**: The `.env` file is now **copied into the image** when you build it.
    *   ⚠️ **Crucial**: Every time you change `.env`, you must run `docker compose up -d --build` to update the image.

## Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/JuanLuBcn/VitaeRules.git
    cd VitaeRules
    ```

2.  **Configure Environment**
    Copy the example environment file and edit it:
    ```bash
    cp .env.example .env
    nano .env
    ```
    *   **OLLAMA_BASE_URL**: Since Ollama is already installed on your Pi, set this to:
        ```ini
        OLLAMA_BASE_URL=http://host.docker.internal:11434
        ```
        *(The `docker-compose.yml` is configured to map this address to your Pi's host IP).*
    *   Add your Telegram Bot Token.

3.  **Start the App**
    
    **Option A: Using Docker Compose (Recommended if it works)**
    ```bash
    docker compose up -d
    ```

    **Option B: Manual Docker Run (If Compose fails)**
    If you see errors like `unknown shorthand flag`, use these commands:

    1.  **Build the image**:
        ```bash
        docker build -t vitaerules:latest .
        ```
    2.  **Run the container**:
        ```bash
        ```

    This will start only the VitaeRules bot. It assumes Ollama is already listening on port 11434 on the host.

## Setting up the LLM (Existing Ollama)

Since you already have Ollama installed, just ensure you have a suitable model pulled. Run this in your Pi's terminal (not inside Docker):

1.  **Pull a lightweight model:**
    *   **Llama 3.2 (3B)**: Good balance of speed and intelligence.
        ```bash
        ollama pull llama3.2
        ```
    *   **Phi-3.5 (3.8B)**: Very capable small model.
        ```bash
        ollama pull phi3.5
        ```

2.  **Update your `.env` file** to match the model you pulled:
    ```ini
    OLLAMA_MODEL=llama3.2
    ```
    Restart the app if you changed the .env:
    ```bash
    docker compose restart vitaerules
    ```

## Performance Tips for Pi 5

*   **Cooling**: Ensure your Pi 5 has an active cooler. AI inference generates significant heat.
*   **Storage**: Run from an NVMe SSD if possible, or a high-speed A2 microSD card. Database operations (ChromaDB) benefit from fast I/O.
*   **RAM**: If you have the 4GB model, stick to models under 3B parameters (like Qwen 2.5 1.5B or Llama 3.2 1B/3B). If you have 8GB, you can comfortably run 7B/8B models (like Llama 3.1 8B), though they will be slower.

## Home Assistant Integration

Since you are running this on the same Pi as Home Assistant (assuming HA is also in Docker or you are on the same network):

*   **Network**: The `docker-compose.yml` creates a bridge network. If you need VitaeRules to talk to Home Assistant directly (e.g., via API), ensure they can reach each other.
*   **Host Mode**: You can change `network_mode: host` in `docker-compose.yml` to make the container share the Pi's network stack. This is often the easiest way to integrate with local smart home devices.

## Troubleshooting

*   **[Errno 111] Connection refused**:
    *   **Symptom**: Errors like `Error during short_term search: [Errno 111] Connection refused`.
    *   **Cause**: The bot cannot connect to Ollama for memory embeddings. This usually happens because Ollama is listening only on `localhost` (127.0.0.1) and not accepting external connections from the Docker container.
    *   **Fix**: Run the container in "Host Network" mode. Add `--network host` to your docker run command and set `OLLAMA_BASE_URL=http://localhost:11434`.

*   **"Connection refused" to Ollama (General)**: Ensure the container name in `.env` matches the service name in `docker-compose.yml` (default: `http://ollama:11434`).

*   **Slow responses**: The Pi 5 CPU is fast for an SBC, but LLMs are heavy. Expect tokens/sec to be around 4-10 depending on the model size.
