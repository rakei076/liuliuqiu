import os
import time
import hashlib
from flask import Flask, request, make_response, jsonify
import xml.etree.ElementTree as ET
import requests

app = Flask(__name__)

TOKEN = os.getenv("WECHAT_TOKEN", "")
PORT = int(os.getenv("PORT", "9000"))
APPID = os.getenv("WECHAT_APPID", "")
APPSECRET = os.getenv("WECHAT_APPSECRET", "")

def check_signature(args):
    signature = args.get("signature", "")
    timestamp = args.get("timestamp", "")
    nonce = args.get("nonce", "")
    if not (signature and timestamp and nonce and TOKEN):
        return False
    s = "".join(sorted([TOKEN, timestamp, nonce]))
    my_sig = hashlib.sha1(s.encode()).hexdigest()
    return my_sig == signature

@app.route("/healthz")
def healthz():
    return jsonify(ok=True, ts=int(time.time()))

@app.route("/wechat", methods=["GET", "POST"])
def wechat():
    # 1) 微信服务器校验
    if request.method == "GET":
        if check_signature(request.args):
            return request.args.get("echostr", "")
        return ("forbidden", 403)

    # 2) 收到用户消息（POST）
    if not check_signature(request.args):
        return ("forbidden", 403)

    xml_data = request.data
    try:
        root = ET.fromstring(xml_data)
    except Exception:
        return ("bad xml", 400)

    from_user = root.findtext("FromUserName", "")
    to_user = root.findtext("ToUserName", "")
    msg_type = root.findtext("MsgType", "")
    content = root.findtext("Content", "") or ""

    # 简单回显：收到什么文本就回什么；非文本回固定提示
    if msg_type == "text":
        reply_text = content
    else:
        reply_text = "收到~（目前仅回显文本）"

    resp_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply_text}]]></Content>
</xml>"""
    resp = make_response(resp_xml)
    resp.headers["Content-Type"] = "application/xml"
    return resp

# 可选：演示“客服消息”主动推送（需48小时内有互动，且配置 APPID/APPSECRET）
def get_access_token():
    if not (APPID and APPSECRET):
        return None
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
    r = requests.get(url, timeout=5)
    data = r.json()
    return data.get("access_token")

@app.route("/send", methods=["POST"])
def send_kf_msg():
    # body: {"openid":"用户openid","text":"要发的内容"}
    data = request.get_json(silent=True) or {}
    openid = data.get("openid", "")
    text = data.get("text", "")
    if not openid or not text:
        return ("missing openid or text", 400)
    token = get_access_token()
    if not token:
        return ("missing appid/appsecret or token", 400)
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    payload = {"touser": openid, "msgtype": "text", "text": {"content": text}}
    r = requests.post(url, json=payload, timeout=5)
    return (r.text, r.status_code)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)