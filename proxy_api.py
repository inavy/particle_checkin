import sys
import time
import logging
import argparse
import requests
from typing import List, Dict, Any, Optional
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from conf import DEF_CLASH_API_PORT
from conf import DEF_CLASH_API_SECRETKEY
from conf import logger

"""
# noqa
# 获取所有代理
curl -X GET http://127.0.0.1:9090/proxies -H "Authorization: Bearer {API_SecretKey}"
# 切换代理
curl -X PUT http://127.0.0.1:9090/proxies/Proxy \
-H "Authorization: Bearer API_SecretKey" \
-H "Content-Type: application/json" \
-d '{"name": "Australia-AU-2-Rate:1.0"}'
"""


def fetch_proxis(session: requests.Session):
    """
    Function to fetch data from API
    """
    url = f'http://127.0.0.1:{DEF_CLASH_API_PORT}/proxies'
    headers = {
        'Authorization': f'Bearer {DEF_CLASH_API_SECRETKEY}'
    }

    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        data = response.json()
        if isinstance(data, dict):
            return data
        else:
            logger.info('Unexpected data format')
            return None
    except requests.exceptions.RequestException as e:
        logger.info(f'Failed to fetch data due to {str(e)}')
        return None


def put_proxy(proxy_dest, session: requests.Session):
    """
    Function to fetch data from API

    proxy_dest: 目标代理
    """
    url = f'http://127.0.0.1:{DEF_CLASH_API_PORT}/proxies/Proxy'
    headers = {
        'Authorization': f'Bearer {DEF_CLASH_API_SECRETKEY}',
        'Content-Type': 'application/json'
    }
    data = {
        'name': proxy_dest
    }

    try:
        response = session.put(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return True
    except requests.exceptions.RequestException as e:
        logger.info(f'Failed to change proxy due to {str(e)}')
        return False


def get_proxy_current():
    """
    Return:
        获取当前的代理名称

    proxy_now:
        string
    """
    # Set up a session with retries
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    data = fetch_proxis(session)
    d_proxies = data.get('proxies', {})

    d_selector = d_proxies['Proxy']
    proxy_now = d_selector['now']

    return proxy_now


def get_proxy_list():
    """
    Return:
        (proxy_now, lst_available)

    proxy_now:
        string
    lst_available:
        [[proxy_name, mean_delay], [proxy_name, mean_delay]]
    """
    # Set up a session with retries
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    data = fetch_proxis(session)
    d_proxies = data.get('proxies', {})

    d_selector = d_proxies['Proxy']
    proxy_now = d_selector['now']
    lst_proxy = d_selector['all']

    lst_available = []
    for proxy_name in lst_proxy:
        if proxy_name == 'Auto':
            continue
        if proxy_name.startswith('Valid until'):
            continue
        if proxy_name in d_proxies:
            lst_history = d_proxies[proxy_name]['history']
            if len(lst_history) == 1:
                mean_delay = lst_history[0]['meanDelay']
                # print(proxy_name, mean_delay)
                lst_available.append([proxy_name, mean_delay])
            else:
                # print(proxy_name)
                pass

    # 使用列表的 sort 方法进行排序
    lst_available.sort(key=lambda x: x[1])

    # 打印排序后的列表
    logger.info(f'proxy_now: {proxy_now}')
    for proxy_name, mean_delay in lst_available:
        logger.info(f'{proxy_name} mean_delay:{mean_delay}')

    return (proxy_now, lst_available)


def change_proxy(black_list=[]):
    """
    black_list: proxy_name black list
    切换成功，返回新的切换后的代理名称
    切换失败，返回当前未切换的代理名称
    """
    # Set up a session with retries
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))

    proxy_dest = ''

    (proxy_now, lst_available) = get_proxy_list()
    for (s_proxy, mean_delay) in lst_available:
        if s_proxy == proxy_now:
            continue
        if s_proxy in black_list:
            continue
        proxy_dest = s_proxy
        break

    b_success = put_proxy(proxy_dest, session)
    logger.info(f'proxy_old:{proxy_now}, proxy_new:{proxy_dest}')

    if b_success:
        return proxy_dest
    else:
        return proxy_now


def main(args):
    """
    """
    if args.get_proxy_list:
        get_proxy_list()
    elif args.change_proxy:
        change_proxy()
    else:
        print('Usage: python {} -h'.format(sys.argv[0]))


if __name__ == '__main__':
    """
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--get_proxy_list', required=False, action='store_true',
        help='获取 proxy 列表及延迟'
    )
    parser.add_argument(
        '--change_proxy', required=False, action='store_true',
        help='选择 proxy'
    )
    args = parser.parse_args()
    main(args)
