"""
utils
"""
import sys
import json
import requests
from datetime import datetime
from dateutil import tz
from datetime import timezone
import socket
import time

DEF_URL_DINGTALK = "https://oapi.dingtalk.com/robot/send"
access_token = "0313ed7471f2910596c1d91cef6569c132"  # noqa


def conv_time(ts, style=1):
    """
    ts: second
    style:
        1: 2022-10-20
        2: 2022-10-20T20:51:11+0800
        3: 2022-10-20 00:00:00
        4: 20:51
        5: 2022-10-20 20:51:11
    """
    to_zone = tz.gettz('Asia/Shanghai')
    if style == 1:
        t_format = "%Y-%m-%d"
    elif style == 2:
        t_format = "%Y-%m-%dT%H:%M:%S+0800"
    elif style == 3:
        t_format = "%Y-%m-%d 00:00:00"
    elif style == 4:
        t_format = "%H:%M"
    elif style == 5:
        t_format = "%Y-%m-%d %H:%M:%S"
    else:
        print("conv_time parameter is error.")
        sys.exit(1)
    dt = datetime.utcfromtimestamp(ts)
    # local = dt.astimezone(to_zone)
    local = dt.replace(tzinfo=timezone.utc).astimezone(to_zone)
    s_date = local.strftime(t_format)
    return s_date


def get_host_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def ding_msg(content, access_token, msgtype="markdown"):
    lst_phone = []

    s_ip = get_host_ip()
    if "markdown" == msgtype:
        content["text"] += (
            "\n###### Update:{time}"
            "\n###### From:{ip}".format
            (
                time=conv_time(time.time(), 5),
                ip=s_ip
            )
        )
    else:
        content += (
            "\nUpdate:{time}"
            "\nFrom:{ip}".format
            (
                time=conv_time(time.time(), 5),
                ip=s_ip
            )
        )
    data = {
        "msgtype": msgtype,
        msgtype: content,
        "at": {
            "atMobiles": lst_phone,
            "isAtAll": False
        }
    }
    data = json.dumps(data)
    print(data)

    headers = {"Content-Type": "application/json; charset=utf-8"}
    resp = requests.post(
        url="{0}?access_token={1}".format(DEF_URL_DINGTALK, access_token),
        data=data,
        headers=headers,
        timeout=3
    )

    print(resp.content)


def ts_human(n_sec):
    s_ret = ""
    n_hour = 0
    n_min = 0
    n_sec = int(n_sec)
    if n_sec >= 3600:
        n_hour = int(n_sec / 3600)
        n_sec = n_sec % 3600
    if n_sec >= 60:
        n_min = int(n_sec / 60)
        n_sec = int(n_sec % 60)

    if n_hour:
        s_ret += "{}h".format(n_hour)
    if n_min:
        s_ret += "{}m".format(n_min)
    if n_sec:
        s_ret += "{}s".format(n_sec)

    return s_ret


def get_date(is_utc=True):
    # 获取当前 UTC 时间的日期
    now = datetime.utcnow()

    # 格式化为 yyyymmdd
    s_date = now.strftime('%Y%m%d')

    return s_date


if __name__ == "__main__":
    """
    """
    s_token = 'ff930a850a7feebb7db0ea1f0e5b3032f175dab'  # noqa
    d_cont = {
        'title': 'my title',
        'text': (
            '- first line\n'
            '- second line\n'
        )
    }
    ding_msg(d_cont, s_token, msgtype="markdown")
