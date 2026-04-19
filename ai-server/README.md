# Local AI agent server (FastAPI + Ollama + tools)

Python service that chats through Ollama, returns strict JSON from the model, and runs registered tools (files, Tavily web search, etc.).

## Security note about API keys

**Do not paste Tavily (or any) API keys into chat, issues, or commits.** Set `TAVILY_API_KEY` only on the machine that runs this server (environment variable or a private `.env` that is gitignored).

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com) running on the same host (or reachable at `OLLAMA_URL`)
- Optional: [Tavily](https://tavily.com) API key for the `tavily_search` tool

## Quick start (Ubuntu or macOS)

If you cloned a repo whose **root folder already contains** `app.py` and `requirements.txt`, run the following **from that folder** (do not add an extra `cd ai-server`). If this project lives as `ai-server/` inside a larger repo, `cd ai-server` first.

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

ollama pull qwen2.5:7b-instruct   # or match OLLAMA_MODEL

export TAVILY_API_KEY='tvly-...'   # optional, for web search tool

uvicorn app:app --host 0.0.0.0 --port 8000
```

- API docs (browser): `http://<host>:8000/docs`
- Health: `GET /health`
- Chat: `POST /chat` with JSON body `{"message":"..."}`

## GitHub deploy workflow

1. Create a **private** GitHub repo if the server will hold secrets in deployment config.
2. From your dev machine:

   ```bash
   cd ai-server
   git init
   git add .
   git commit -m "Initial ai-server"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

3. On Ubuntu:

   ```bash
   git clone https://github.com/<you>/<repo>.git
   cd <repo>   # if the service files are in a subfolder, also: cd ai-server
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Set secrets on the server (example):

   ```bash
   export TAVILY_API_KEY='tvly-...'
   export OLLAMA_URL='http://127.0.0.1:11434'
   ```

5. Run behind Tailscale (see below) or systemd with `EnvironmentFile`.

## Access from your Mac over Tailscale

1. **Install and log in to Tailscale** on both the Ubuntu server and your Mac (same tailnet).
2. On **Ubuntu**, find the Tailscale IP:

   ```bash
   tailscale ip -4
   ```

3. Start the API bound to all interfaces (already shown):

   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8000
   ```

4. On **Ubuntu**, if `ufw` is enabled, allow the port:

   ```bash
   sudo ufw allow 8000/tcp
   sudo ufw reload
   ```

5. On your **Mac** browser, open:

   - `http://<ubuntu-tailscale-ipv4>:8000/docs` — interactive Swagger UI  
   - or `http://<ubuntu-tailscale-ipv4>:8000/health`

So yes: **`http://<Tailscale-IP-of-Ubuntu>:8000`** (port is whatever you pass to `--port`, default **8000**).

If the page does not load, confirm both machines show `tailscale status` as connected, Ollama is running on the server, and nothing else is blocking port 8000.

## Environment variables

| Variable | Purpose |
|----------|---------|
| `OLLAMA_URL` | Ollama base URL (default `http://127.0.0.1:11434`) |
| `OLLAMA_MODEL` | Model tag (default `qwen2.5:7b-instruct`) |
| `TAVILY_API_KEY` | Enables `tavily_search` tool |
| `TAVILY_TIMEOUT_S` | Tavily HTTP timeout seconds (default `60`) |
| `AI_SERVER_WORK_DIR` | Directory for generated files (default `generated_files`) |
| `DEBUG` | `true` / `false` |

See `.env.example` for a template (copy to `.env` locally if you use a secrets manager that sources it; keep `.env` out of git).
