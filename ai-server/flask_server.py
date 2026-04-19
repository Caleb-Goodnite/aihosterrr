import asyncio
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from agent import AgentService
from config import DEBUG, WORK_DIR
from tools.file_tools import ensure_workdir
from utils.logger import configure_logging, get_logger

logger = get_logger(__name__)
_agent_service = AgentService()

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
async def chat():
    data = request.json
    message = data.get("message")
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    try:
        # Agent.chat is an async function
        response = await _agent_service.agent.chat(message)
        return jsonify({
            "type": response.type,
            "content": response.content,
            "file": response.file
        })
    except Exception as exc:
        logger.exception("unhandled /chat failure")
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    configure_logging()
    ensure_workdir()
    logger.info("starting flask-ai-server | workdir=%s | debug=%s", WORK_DIR, DEBUG)
    app.run(host="0.0.0.0", port=5001, debug=DEBUG)
