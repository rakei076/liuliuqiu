import hashlib, time, xml.etree.ElementTree as ET
from typing import Dict

def check_signature(token: str, signature: str, timestamp: str, nonce: str) -> bool:
    if not (token and signature and timestamp and nonce):
        return False
    arr = [token, timestamp, nonce]
    arr.sort()
    sha = hashlib.sha1()
    sha.update("".join(arr).encode("utf-8"))
    return sha.hexdigest() == signature

def parse_xml_message(xml_bytes: bytes) -> Dict[str, str]:
    root = ET.fromstring(xml_bytes)
    data = {}
    for child in root:
        data[child.tag] = child.text
    return data

def build_text_reply(to_user: str, from_user: str, content: str) -> str:
    now = int(time.time())
    return f"""<xml>
<ToUserName><![CDATA[{to_user}]]></ToUserName>
<FromUserName><![CDATA[{from_user}]]></FromUserName>
<CreateTime>{now}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{content}]]></Content>
</xml>"""