import os
import time
import json
import logging
from flask import Flask, request, make_response
import requests
from dotenv import load_dotenv

from wechat_utils import check_signature, parse_xml_message, build_text_reply

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("wechat-webhook")

WECHAT_TOKEN = os.getenv("WECHAT_TOKEN", "")
SCF_API_URL = os.getenv("SCF_API_URL", "")
SCF_API_KEY = os.getenv("SCF_API_KEY", "")

if not WECHAT_TOKEN:
    logger.warning("WECHAT_TOKEN 未设置，请在环境变量中配置。")

app = Flask(__name__)

@app.route("/healthz", methods=["GET"])
def health():
    return {"ok": True, "ts": int(time.time())}

@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    if request.method == "GET":
        signature = request.args.get("signature", "")
        timestamp = request.args.get("timestamp", "")
        nonce = request.args.get("nonce", "")
        echostr = request.args.get("echostr", "")

        if check_signature(WECHAT_TOKEN, signature, timestamp, nonce):
            return make_response(echostr)
        else:
            logger.warning("GET 签名校验失败。")
            return make_response("invalid signature", 403)

    raw_xml = request.data
    try:
        msg = parse_xml_message(raw_xml)
    except Exception as e:
        logger.exception("解析 XML 失败: %s", e)
        return make_response("")

    msg_type = msg.get("MsgType", "")
    from_user = msg.get("FromUserName", "")
    to_user = msg.get("ToUserName", "")

    placeholder = "我在思考啦，请稍等～"
    reply_xml = build_text_reply(to_user=from_user, from_user=to_user, content=placeholder)

    if msg_type == "text":
        user_text = (msg.get("Content") or "").strip()
        payload = {
            "openid": from_user,
            "text": user_text,
            "msg_type": "text",
            "ts": int(time.time()),
            "msg_id": msg.get("MsgId"),
        }
        if SCF_API_URL:
            try:
                headers = {"Content-Type": "application/json"}
                if SCF_API_KEY:
                    headers["X-API-Key"] = SCF_API_KEY
                resp = requests.post(SCF_API_URL, data=json.dumps(payload), headers=headers, timeout=5)
                if resp.status_code >= 300:
                    logger.warning("SCF 调用非 2xx: %s %s", resp.status_code, resp.text[:200])
            except Exception as e:
                logger.exception("调用 SCF 失败: %s", e)
        else:
            logger.warning("未设置 SCF_API_URL，AI 回复将无法发送。")
    else:
        logger.info("收到非文本消息类型: %s", msg_type)

    return make_response(reply_xml)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)