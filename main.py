import os
import sys # noqa
import argparse
import random
import re
import time
import copy

from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
from DrissionPage._elements.none_element import NoneElement

from fun_utils import ding_msg
from fun_utils import get_date
from fun_utils import load_file
from fun_utils import save2file
# from proxy_utils import change_proxy
from proxy_api import change_proxy
from proxy_api import get_proxy_current

from conf import DEF_LOCAL_PORT
from conf import DEF_USE_HEADLESS
from conf import DEF_DEBUG
from conf import DEF_PATH_USER_DATA
from conf import DEF_PWD
from conf import DEF_IP_FULL
from conf import DEF_MSG_SUCCESS
from conf import DEF_MSG_FAIL
from conf import DEF_MSG_IP_FULL
from conf import DEF_NUM_NFT
from conf import DEF_NUM_TRY_CHECKIN
from conf import DEF_NUM_TRY_PURCHASE_NFT
from conf import DEF_DING_TOKEN
from conf import DEF_BALANCE_USDG_MIN
from conf import DEF_MSG_BALANCE_ERR
from conf import DEF_PATH_BROWSER
from conf import DEF_AUTO_PROXY
from conf import DEF_PATH_DATA_PROXY
from conf import DEF_CHECKIN
from conf import DEF_PATH_DATA_STATUS
from conf import DEF_HEADER_STATUS
from conf import logger

"""
2024.09.05
1. 增加启动参数

2024.09.04
1. 通过 ClashX API 切换代理

2024.09.01
1. 多个账号的执行结果写到一个文件中

2024.08.30
1. 切换 IP 后，可能出现异常(与页面的连接已断开)，增加重试

2024.08.29
1. 在关键确认步骤确保页面加载完成
self.page.wait.load_start()
不追求速度，慢就是快
2. Check-in 增加 Already checked-in Toastify 检查

2024.08.28
1. 通过 pyautogui 切换 proxy
注意，锁屏下无法操作

2024.08.27
1. INSUFFICIENT BALANCE
当余额不足时，发消息提醒，手动 Deposit
2. 页面改版，适配
JOINNOW 变为了 JOIN NOW
3. 封装成 Class，便于传递成员变量

2024.08.25
1. 基于 drissionpage
https://drissionpage.cn/QandA
2. 当出现 cloudflare 5秒盾 真人验证，需手动点击
3. 一个 IP 每天只能做 20次左右的交互，提示 ip full 时，需要手动更换 IP
4. IP FULL 钉钉告警
5. 支持无头浏览器模式
"""


class ParticleTask():
    def __init__(self) -> None:
        self.args = None
        self.page = None
        # self.usdg = -1
        self.proxy_name = 'UNKNOWN(START)'
        self.proxy_info = 'USING'
        self.lst_proxy_cache = []
        self.lst_proxy_black = []
        self.s_today = get_date(is_utc=True)
        self.file_proxy = None
        self.init_proxy()

        # 账号执行情况
        self.dic_status = {}

    def set_args(self, args):
        self.args = args
        self.usdg = -1
        self.init_proxy()
        self.status_load()

    def __del__(self):
        self.proxy_save()
        self.status_save()
        logger.info(f'Exit {self.args.s_profile}')

    def status_load(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status_{self.s_today}.csv'
        self.dic_status = load_file(
            file_in=self.file_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def status_save(self):
        self.file_status = f'{DEF_PATH_DATA_STATUS}/status_{self.s_today}.csv'
        self.dic_status = save2file(
            file_ot=self.file_status,
            dic_status=self.dic_status,
            idx_key=0,
            header=DEF_HEADER_STATUS
        )

    def init_proxy(self):
        if DEF_AUTO_PROXY:
            self.s_today = get_date(is_utc=True)
            self.file_proxy = f'{DEF_PATH_DATA_PROXY}/proxy_{self.s_today}.csv'
            self.lst_proxy_black = self.proxy_load()
            self.proxy_name = change_proxy(self.lst_proxy_black)
            logger.info(f'已开启自动更换 Proxy ，当前代理是 {self.proxy_name}')

    def close(self):
        # 在有头浏览器模式 Debug 时，不退出浏览器，用于调试
        if DEF_USE_HEADLESS is False and DEF_DEBUG:
            pass
        else:
            self.page.quit()

    def proxy_update(self, proxy_update_info):
        self.proxy_info = proxy_update_info
        self.proxy_save()
        self.lst_proxy_black = self.proxy_load()
        logger.info(f'准备更换 Proxy ，更换前的代理是 {self.proxy_name}')
        self.proxy_name = change_proxy(self.lst_proxy_black)
        logger.info(f'完成更换 Proxy ，更换后的代理是 {self.proxy_name}')
        self.proxy_info = 'USING'

    def proxy_load(self):
        lst_proxy_black = []

        if not DEF_AUTO_PROXY:
            return lst_proxy_black

        try:
            with open(self.file_proxy, 'r') as fp:
                # Skip the header line
                # next(fp)
                for line in fp:
                    if len(line.strip()) == 0:
                        continue
                    # 逗号分隔，Proxy Info 可能包含逗号
                    fields = line.strip().split(',')
                    proxy_name = fields[0]
                    proxy_info = ', '.join(fields[1:])
                    self.lst_proxy_cache.append([proxy_name, proxy_info])
                    if proxy_info in [DEF_MSG_IP_FULL, DEF_MSG_FAIL]:
                        lst_proxy_black.append(proxy_name)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.info(f'[proxy_load] An error occurred: {str(e)}')

        return lst_proxy_black

    def proxy_save(self):
        if not DEF_AUTO_PROXY:
            return

        if not self.proxy_name:
            return

        if not self.file_proxy:
            self.s_today = get_date(is_utc=True)
            self.file_proxy = f'{DEF_PATH_DATA_PROXY}/proxy_{self.s_today}.csv'

        dir_file_out = os.path.dirname(self.file_proxy)
        if dir_file_out and (not os.path.exists(dir_file_out)):
            os.makedirs(dir_file_out)

        if not os.path.exists(self.file_proxy):
            with open(self.file_proxy, 'w') as fp:
                fp.write('Proxy Name,Proxy Info\n')

        b_new_proxy_name = True
        try:
            # 先读取原有内容以便更新
            proxies = []
            if os.path.exists(self.file_proxy):
                with open(self.file_proxy, 'r') as fp:
                    lines = fp.readlines()
                    for line in lines[1:]:  # 跳过头部
                        proxies.append(tuple(line.strip().split(',')))

            with open(self.file_proxy, 'w') as fp:
                fp.write('Proxy Name,Proxy Info\n')
                for fields in proxies:
                    proxy_name = fields[0]
                    proxy_info = ','.join(fields[1:])
                    if proxy_name == self.proxy_name:
                        proxy_info = self.proxy_info
                        b_new_proxy_name = False
                    fp.write(f'{proxy_name},{proxy_info}\n')  # noqa
                if b_new_proxy_name:
                    fp.write(f'{self.proxy_name},{self.proxy_info}\n')  # noqa
        except Exception as e:
            logger.info(f'[proxy_save] An error occurred: {str(e)}')

    def initChrome(self, s_profile):
        """
        s_profile: 浏览器数据用户目录名称
        """
        profile_path = s_profile

        co = ChromiumOptions()

        # 设置本地启动端口
        co.set_local_port(port=DEF_LOCAL_PORT)
        if len(DEF_PATH_BROWSER) > 0:
            co.set_paths(browser_path=DEF_PATH_BROWSER)
        # co.set_paths(browser_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome') # noqa

        # 阻止“自动保存密码”的提示气泡
        co.set_pref('credentials_enable_service', False)

        # 阻止“要恢复页面吗？Chrome未正确关闭”的提示气泡
        co.set_argument('--hide-crash-restore-bubble')

        co.set_user_data_path(path=DEF_PATH_USER_DATA)
        co.set_user(user=profile_path)

        # https://drissionpage.cn/ChromiumPage/browser_opt
        co.headless(DEF_USE_HEADLESS)
        co.set_user_agent(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36') # noqa

        try:
            self.page = ChromiumPage(co)

            # logger.info(co.browser_path)

            # page.get('https://pioneer.particle.network/zh-CN/point')
            # page.get('http://DrissionPage.cn')
            # page.quit()
        except Exception as e:
            logger.info(f'Error: {e}')
        finally:
            pass

    def open_okx(self):
        """
        https://chrome.google.com/webstore/detail/mcohilncbfahbmgdjkbpemcciiolgcge
        """
        EXTENSION_ID = 'mcohilncbfahbmgdjkbpemcciiolgcge'
        logger.info('Open okx to login ...')
        self.page.get('chrome-extension://{}/home.html'.format(EXTENSION_ID))
        self.page.wait.load_start()

        # 页面上如果没有Web3，可能是没有安装插件
        if not self.page.ele('Web3', timeout=2):
            logger.info('打开 OKX 插件页安装插件')
            self.page.get('https://chrome.google.com/webstore/detail/mcohilncbfahbmgdjkbpemcciiolgcge') # noqa
            time.sleep(60)

        ele_input = self.page.ele('@data-testid=okd-input', timeout=2)
        if not isinstance(ele_input, NoneElement):
            logger.info('OKX 输入密码')
            ele_input.input(DEF_PWD)
            logger.info('OKX 登录')
            self.page.ele('@data-testid=okd-button').click()

        x_path = '//*[@id="home-page-root-element-id"]/div[2]/div'
        balance = self.page.ele('x:{}'.format(x_path), timeout=2)
        if not isinstance(balance, NoneElement):
            logger.info('账户余额：{}'.format(balance.text))
        else:
            logger.info(
                'ERROR! okx is invalid! profile:{}'
                .format(self.args.s_profile)
            )
            if DEF_USE_HEADLESS:
                self.page.quit()
            # sys.exit(-1)
        logger.info('okx login success')

    def okx_confirm(self):
        logger.info('准备 OKX Wallet Confirm ...')
        self.page.wait.load_start()
        # 当出现 cloudflare 时，勾选
        try:
            button = self.page.ele('x://*[@id="RlquG0"]/div/label/input')
            logger.info(button.text)
            button.click()
        except: # noqa
            pass

        if len(self.page.tab_ids) == 2:
            tab_id = self.page.latest_tab
            tab_new = self.page.get_tab(tab_id)
            try:
                buttons = tab_new.eles('@data-testid=okd-button')
                buttons[-1].click()
            except: # noqa
                pass

    def check_network(self):
        if len(self.page.html) == 0:
            s_proxy_pre = self.proxy_name
            logger.info('无法获取页面内容，请检查网络')
            if DEF_AUTO_PROXY:
                self.proxy_update(DEF_MSG_FAIL)

            if len(DEF_DING_TOKEN) > 0:
                d_cont = {
                    'title': '无法获取页面内容 [Particle]',
                    'text': (
                        '- 页面为空\n'
                        '- 请检查网络\n'
                        '- profile: {s_profile}\n'
                        '- proxy_pre: {s_proxy_pre}\n'
                        '- proxy_now: {s_proxy_now}\n'
                        .format(
                            s_profile=self.args.s_profile,
                            s_proxy_pre=s_proxy_pre,
                            s_proxy_now=self.proxy_name
                        )
                    )
                }
                ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")
            self.page.quit()

        try:
            # 检查网络连接是否正常
            x_path = '//*[@id="error-information-popup-content"]/div[2]'
            s_info = self.page.ele('x:{}'.format(x_path), timeout=2).text
            if 'ERR_CONNECTION_RESET' == s_info:
                s_proxy_pre = self.proxy_name
                logger.info('无法访问此网站')

                if DEF_AUTO_PROXY:
                    self.proxy_update(DEF_MSG_FAIL)

                if len(DEF_DING_TOKEN) > 0:
                    d_cont = {
                        'title': 'Network Error',
                        'text': (
                            '- 无法访问此网站\n'
                            '- 连接已重置\n'
                            '- profile: {s_profile}\n'
                            '- proxy_pre: {s_proxy_pre}\n'
                            '- proxy_now: {s_proxy_now}\n'
                            .format(
                                s_profile=self.args.s_profile,
                                s_proxy_pre=s_proxy_pre,
                                s_proxy_now=self.proxy_name
                            )
                        )
                    }
                    ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")
                self.page.quit()
        except: # noqa
            pass

    def check_ip_full(self):
        try:
            toastify = self.page.ele('x://*[@id="1"]/div[1]/div[2]', timeout=2).text # noqa
        except: # noqa
            toastify = ''
        if len(toastify) > 0:
            logger.info('toastify={}'.format(toastify))

        if toastify == DEF_IP_FULL:
            # s_proxy_pre = self.proxy_name
            s_proxy_pre = get_proxy_current()
            if DEF_AUTO_PROXY:
                self.proxy_update(DEF_MSG_IP_FULL)
                time.sleep(3)

            if len(DEF_DING_TOKEN) > 0:
                d_cont = {
                    'title': 'ip is full',
                    'text': (
                        '- The number of times this ip sent today is full\n'
                        '- please try again tomorrow\n'
                        '- profile: {s_profile}\n'
                        '- proxy_pre: {s_proxy_pre}\n'
                        '- proxy_now: {s_proxy_now}\n'
                        .format(
                            s_profile=self.args.s_profile,
                            s_proxy_pre=s_proxy_pre,
                            s_proxy_now=self.proxy_name
                        )
                    )
                }
                ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")

            logger.info('ERROR! IP is full')
            self.page.quit()

            if DEF_AUTO_PROXY:
                return False
            else:
                return True
        else:
            return False

    def check_in(self):
        """
        Return:
            True: Already Checked-in
            False: To Checkin-in
        """
        for i in range(DEF_NUM_TRY_CHECKIN):
            logger.info('check_in try_i={}'.format(i+1))
            self.page.get('https://pioneer.particle.network/zh-CN/point')

            logger.info('准备 CHECK-IN ...')
            x_path = '//*[@id="portal"]/div[2]/div[2]/div[1]/div/div[4]/div[4]/button/div[1]' # noqa
            self.page.wait.eles_loaded('x:{}'.format(x_path))
            self.page.actions.move_to('x:{}'.format(x_path))

            # 等页面都加载完，网速慢的时候，按钮状态未更新
            self.page.wait.load_start()

            # 首次不 sleep ，失败后从第二次开始，增加 sleep
            if i > 0:
                logger.info('sleep {} seconds...'.format(i+1))
                time.sleep(i+1)
            button = self.page.ele('x:{}'.format(x_path))
            if isinstance(button, NoneElement):
                logger.info('没有 CHECK-IN 按钮，从头重试 ...')
                continue

            if button.text == 'Checked in':
                logger.info('Oh! Check-in is already done before!')
                return True

            if button.text == 'Check-in':
                # 2024.08.27 无法点击，改为使用 js 点击，成功
                button.click(by_js=True)
            else:
                logger.info('button.text={}'.format(button.text))

            try:
                toastify = self.page.ele('x://*[@id="1"]/div[1]/div[2]', timeout=2).text # noqa
            except: # noqa
                toastify = ''
            if len(toastify) > 0:
                if toastify == DEF_CHECKIN:
                    logger.info('Check-in is success!')
                    return True
                else:
                    logger.info('toastify={}'.format(toastify))

            # SEND TRANSACTION 窗口
            x_path = '/html/body/div[4]/div/div[2]/div/div/div[1]'
            button = self.page.ele('x:{}'.format(x_path), timeout=2)
            if isinstance(button, NoneElement):
                logger.info('没有 SEND TRANSACTION 窗口，从头重试 ...')
                continue

            logger.info('准备点击 CONFIRM 按钮')
            x_path = '//html/body/div[4]/div/div[2]/div/div/div[2]/div[4]/div[2]/button/div[1]' # noqa
            button = self.page.ele('x:{}'.format(x_path), timeout=10)
            if isinstance(button, NoneElement):
                logger.info('没有 CONFIRM 按钮，从头重试 ...')
                continue
            button.click()

            logger.info('准备 OKX CONFIRM')
            self.okx_confirm()
            if self.check_ip_full():
                if DEF_USE_HEADLESS:
                    self.page.quit()
                # sys.exit(-1)
                break
            logger.info('Check-in is Finished!')

        return False

    def activate(self):
        """
        # noqa
        激活后回到 PURCHASE 页面
        # DEF_URL_ACTIVATE = 'https://pioneer.particle.network/zh-CN/accountAnimation'
        # DEF_URL_SIGNUP = 'https://pioneer.particle.network/zh-CN/signup'
        """
        # page.wait.load_start()
        logger.info('Current url: {}'.format(self.page.url))

        try:
            # 图片
            x_path = '/html/body/div[1]/div[1]/div/div[1]/div[3]/div[3]/img' # noqa
            self.page.wait.eles_loaded('x:{}'.format(x_path))

            # DrissionPage.errors.NoRectError: 该元素没有位置及大小
            time.sleep(1)

            button = self.page.ele('x:{}'.format(x_path)) # noqa
            if isinstance(button, NoneElement):
                logger.info('NO ACTIVATE PAGE')
            else:
                logger.info('CLICK TO ACTIVATE')
                if DEF_DEBUG:
                    print(self.page.tab_ids)
                button.click()
        except: # noqa
            logger.info('没有 CLICK TO ACTIVATE')
            # return False

        logger.info('Current url: {}'.format(self.page.url))

        # CLICK TO LAUNCH
        logger.info('CLICK TO LAUNCH ...')
        try:
            x_path = '/html/body/div[1]/div[1]/div/div[1]/a/div'
            button = self.page.ele('x:{}'.format(x_path))
            logger.info('button.text={}'.format(button.text))
            if isinstance(button, NoneElement):
                logger.info('没有 CLICK TO LAUNCH')
            elif button.text == 'Click to launch':
                button.click()
                logger.info('CLICK TO LAUNCH, SUCCESS')
            else:
                logger.info('不是想要的按钮：{}'.format(button.text))
        except: # noqa
            logger.info('没有 CLICK TO LAUNCH')
            # return False

        # LAUNCH
        logger.info('TO LAUNCH ...')
        try:
            time.sleep(1)
            x_path = '//*[@id="home"]/div/div[1]/div/div[2]/a/div[1]'
            button = self.page.ele('x:{}'.format(x_path))
            logger.info('button.text={}'.format(button.text))
            if button.text == 'LAUNCH':
                button.click()
                logger.info('LAUNCH SUCCESS')
                return True
        except: # noqa
            logger.info('没有 LAUNCH')
            return False

        return True

    def check_nft_num(self):
        """
        返回值 num_ret
        [1, 5]
        第一个数: 今天成功购买的 NFT 数量
        第二个数: 今天计算积分的 NFT 数量，超出该数量不算积分
        """
        num_ret = [0, 0]

        for i in range(DEF_NUM_TRY_PURCHASE_NFT):
            logger.info(f'check_nft_num try_i={i+1}/{DEF_NUM_TRY_PURCHASE_NFT}') # noqa
            self.page.get('https://pioneer.particle.network/zh-CN/point')

            # logger.info('即将刷新页面 {}'.format(page.url))
            self.page.refresh()

            x_path = '//*[@id="portal"]/div[2]/div[2]/div[4]/div/div[4]/div/div' # noqa
            self.page.wait.eles_loaded('x:{}'.format(x_path))
            self.page.actions.move_to('x:{}'.format(x_path))

            # 等页面都加载完，网速慢的时候，按钮状态未更新
            self.page.wait.load_start()
            # time.sleep(3)

            button = self.page.ele('x:{}'.format(x_path), timeout=2)
            if isinstance(button, NoneElement):
                pass
            elif button.text.startswith('Attempts today'):
                # Attempts today: 11 / 5
                logger.info('NFT {}'.format(button.text))

                # 使用正则表达式提取数字
                numbers = re.findall(r'\d+', button.text)

                # 将提取到的数字转换为整数
                numbers = [int(num) for num in numbers]

                # 输出结果
                # print(numbers)  # 输出: [11, 5]
                if len(numbers) == 2:
                    num_ret = numbers
                    break
            else:
                pass
        return num_ret

    def check_balance(self, s_balance):
        """
        确认账户余额
        True 余额充足
        False 余额不足
        """
        try:
            flt_balance = float(s_balance.replace(',', ''))
        except: # noqa
            flt_balance = 0

        self.usdg = int(flt_balance)

        if flt_balance < DEF_BALANCE_USDG_MIN:
            if len(DEF_DING_TOKEN) > 0:
                d_cont = {
                    'title': 'insufficient balance',
                    'text': (
                        '- profile: {}\n'
                        '- balance: ${} 小于 ${}\n'
                        '- please deposit manually\n'
                        .format(
                            self.args.s_profile,
                            flt_balance, DEF_BALANCE_USDG_MIN
                        )
                    )
                }
                ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")
            return False

        return True

    def purchase_nft(self):
        """
        返回值 s_msg
        """
        s_msg = DEF_MSG_FAIL
        for i in range(DEF_NUM_TRY_PURCHASE_NFT):
            logger.info(f'purchase_nft try_i={i+1}/{DEF_NUM_TRY_PURCHASE_NFT} [{self.args.s_profile}]') # noqa
            self.page.get('https://pioneer.particle.network/zh-CN/crossChainNFT') # noqa

            # logger.info('刷新页面 {}'.format(self.page.url))
            # self.page.refresh()

            logger.info('准备在 crossChainNFT 页面点击 PURCHASE 按钮 ...')
            # time.sleep(5)
            self.page.wait.load_start()

            x_path = '//*[@id="content-wrapper"]/div/div[2]/div[1]/div[3]/div[2]/div[4]/button/div[1]' # noqa
            button = self.page.ele('x:{}'.format(x_path), timeout=2)
            if button and button.text == 'Purchase':
                button.click()
            else:
                logger.info('没有 PURCHASE 按钮，重新开始')
                continue

            logger.info('准备选中 USDG 复选框 ...')
            # time.sleep(5)
            self.page.wait.load_start()

            buttons = self.page.eles('.:polygon-small mb-3 flex cursor-pointer') # noqa
            if len(buttons) >= 1:
                # USDG 余额
                s_balance = buttons[0].text.split('$')[-1]
                if len(s_balance) == 0:
                    logger.info('没有获取到 USDG 余额，重新开始')
                    continue
                logger.info(f'USDG 余额: ${s_balance} [{self.args.s_profile}]')
                if not self.check_balance(s_balance):
                    logger.info(f'USDG 余额不足，退出 (余额: ${s_balance}) [{self.args.s_profile}]') # noqa
                    s_msg = DEF_MSG_BALANCE_ERR
                    break
                buttons[0].click()
            else:
                self.activate()
                logger.info('没有 USDG 选项，重新开始')
                continue

            logger.info('准备 Click Next BUTTON ...')
            x_path = '/html/body/div[4]/div/div[2]/div/div/div[2]/div[6]/button/div[1]' # noqa
            button = self.page.ele('x:{}'.format(x_path))
            if button.text == 'Next':
                time.sleep(1)
                if button.states.is_clickable:
                    button.click()
                else:
                    logger.info('注意！Next 按钮不可点击！！！为啥呢？！')
                    continue
            else:
                logger.info('没有 Next 按钮，重新开始')
                continue

            logger.info('准备在 NETWORK FEE 弹窗点击 PURCHASE 按钮 ...')
            x_path = '/html/body/div[4]/div/div[2]/div/div/button/div[1]'
            button = self.page.ele('x:{}'.format(x_path))
            if isinstance(button, NoneElement):
                logger.info('没有 NETWORK FEE 弹窗，重新开始')
                continue
            if button.text == 'Purchase':
                x_path = '/html/body/div[4]/div/div[2]/div/div/div[2]/div[5]/div[1]/div[2]/div[2]' # noqa
                try:
                    fee = self.page.ele('x:{}'.format(x_path), timeout=2).text
                    f_fee = float(fee.replace(',', '').replace('$', ''))
                    if f_fee > 10:
                        logger.info(f'Warning! NETWORK FEE is high! {f_fee}')
                    else:
                        logger.info(f'NETWORK FEE is ${f_fee}')
                except: # noqa
                    pass
                time.sleep(1)
                button.click()
            else:
                logger.info('没有 PURCHASE 按钮，重新开始')
                continue

            # 此处可能会出现 CLOUDFLARE 5秒盾，留点时间
            time.sleep(3)

            self.okx_confirm()
            if self.check_ip_full():
                s_msg = DEF_MSG_IP_FULL
                break

            logger.info('Wait SUCCESSFUL 弹窗 ...')
            time.sleep(1)
            self.page.wait.load_start()
            logger.info('正在确认 SUCCESSFUL 弹窗 ...')
            # 出现 SUCCESSFUL 弹窗，需要等待几秒
            x_path = '/html/body/div[4]/div/div[2]/div/div/div[1]'
            self.page.wait.eles_loaded('x:{}'.format(x_path), timeout=2)
            button = self.page.ele('x:{}'.format(x_path), timeout=2)
            if isinstance(button, NoneElement):
                logger.info('没有 SUCCESSFUL 弹窗，重新开始')
                continue
            else:
                if button.text.startswith('SUCCESSFULLY'):
                    # logger.info('出现 SUCCESSFUL 弹窗')
                    # 弹窗右上角的 ×
                    x_path = '/html/body/div[4]/div/div[2]/div/button'
                    try:
                        self.page.ele('x:{}'.format(x_path)).click()
                        logger.info(f'关闭弹窗 {button.text}')
                    except: # noqa
                        logger.info('未能 SUCCESSFUL 弹窗，忽略')
                        pass
                else:
                    logger.info('button.text:{}'.format(button.text))
                    logger.info('Purchase Failed，重新开始 ...')
                    continue

            s_msg = DEF_MSG_SUCCESS
            break

        if s_msg == DEF_MSG_FAIL:
            s_error = 'PURCHASE_NFT 连续{}次失败'.format(DEF_NUM_TRY_PURCHASE_NFT)
            logger.info(s_error)

        return s_msg

    def particle_login(self):
        try:
            # 首次登录有弹窗，点击 START
            logger.info('正在确认是否有 START 弹窗 ...')
            time.sleep(2)
            x_path = '/html/body/div[1]/button'
            self.page.wait.eles_loaded('x:{}'.format(x_path))
            button = self.page.ele('x:{}'.format(x_path), timeout=2)
            if not isinstance(button, NoneElement):
                logger.info('点击 START')
                button.click()
            else:
                logger.info('没有 START 弹窗')
        except: # noqa
            pass

        self.check_network()

        button = self.page.ele('.polygon-btn-text')
        if isinstance(button, NoneElement):
            logger.info('没有获取到页面右上角按钮')
            return

        logger.info('正在根据按钮[{}]确认登录状态 ...'.format(button.text))
        if button.text in ['JOINNOW', 'JOIN NOW']:
            logger.info('点击 JOINNOW 按钮 ...')
            button.click()

            # 选择登录的钱包
            x_path = '/html/body/div[1]/div[1]/div/div[1]/div[4]/div[3]/div[1]/button' # noqa
            self.page.wait.eles_loaded('x:{}'.format(x_path))
            self.page.actions.move_to('x:{}'.format(x_path))
            button = self.page.ele('x:{}'.format(x_path))
            logger.info('正在点击 OKX WALLET 连接 OKX 钱包 ...')
            button.click(by_js=True)

            # OKX Wallet 连接
            logger.info('OKX Wallet 连接')
            # 需要等待弹窗加载完成
            self.page.wait.load_start()
            if DEF_DEBUG:
                print(self.page.tab_ids)
            if len(self.page.tab_ids) == 2:
                try:
                    tab_id = self.page.latest_tab
                    tab_new = self.page.get_tab(tab_id)
                    button = tab_new.ele('x://*[@id="app"]/div/div/div/div/div[5]/div[2]/button[2]') # noqa
                    logger.info('{}'.format(button.text))
                    button.click()
                except: # noqa
                    pass

            # OKX Wallet 请求签名
            logger.info('OKX Wallet 请求签名')
            self.page.wait.load_start()
            if DEF_DEBUG:
                print(self.page.tab_ids)
            if len(self.page.tab_ids) == 2:
                try:
                    tab_id = self.page.latest_tab
                    tab_new = self.page.get_tab(tab_id)
                    button = tab_new.ele('x://*[@id="app"]/div/div/div/div/div/div[6]/div/button[2]') # noqa
                    logger.info('{}'.format(button.text))
                    button.click()
                except: # noqa
                    pass

            try:
                # 首次登录有弹窗，点击 LAUNCH
                logger.info('确认是否有 LAUNCH 弹窗 ...')
                time.sleep(2)
                x_path = '//*[@id="home"]/div/div[1]/div/div[2]/a'
                if self.page.ele('x:{}'.format(x_path), timeout=2).click():
                    logger.info('成功点击 LAUNCH')
            except: # noqa
                pass

    def particle_init(self):
        """
        登录及校验是否登录成功
        """
        self.page.get('https://pioneer.particle.network/zh-CN/point')

        for i in range(10):
            logger.info('Page Login try_i={}'.format(i+1))
            self.particle_login()

            logger.info('检查是否登录成功 ...')
            time.sleep(1)

            # 这是已登录时的 xpath
            x_path = '//*[@id="navbar"]/header/ul[3]/li/div/button'
            self.page.wait.eles_loaded('x:{}'.format(x_path))
            button = self.page.ele('x:{}'.format(x_path), timeout=2)
            if isinstance(button, NoneElement):
                # 没有获取到已登录的 xpath
                pass
            elif button.text.startswith('0x'):
                logger.info('页面已成功登录')
                break
            else:
                pass

            # 这是未登录时的 xpath
            x_path = '//*[@id="navbar"]/header/ul[3]/li/a/div[1]'
            self.page.wait.eles_loaded('x:{}'.format(x_path))
            button = self.page.ele('x:{}'.format(x_path), timeout=2)
            if isinstance(button, NoneElement):
                logger.info('没有获取到登录状态，从头重试 ...')
                continue

            if button.text in ['JOINNOW', 'JOIN NOW']:
                logger.info('页面未登录，重试 ...')
                continue
            else:
                logger.info('页面已成功登录')
                break

    def particle_nft(self):
        num_nft = [-1, -1]
        logger.info('准备 Purchase NFT ...')
        max_try = int(DEF_NUM_NFT * 1.5)
        for i in range(max_try):
            logger.info('#'*30)
            logger.info(f'### Purchasing, i={i+1}/{max_try} [{self.args.s_profile}]') # noqa
            num_nft = self.check_nft_num()
            if num_nft[1] > 0 and num_nft[0] >= DEF_NUM_NFT:
                break
            s_msg = self.purchase_nft()
            if DEF_MSG_IP_FULL == s_msg:
                break
            if DEF_MSG_BALANCE_ERR == s_msg:
                break
            time.sleep(2)
        return num_nft


def main(args):
    if args.sleep_sec_at_start > 0:
        logger.info(f'Sleep {args.sleep_sec_at_start} seconds at start !!!') # noqa
        time.sleep(args.sleep_sec_at_start)

    if len(args.profile) > 0:
        items = args.profile.split(',')
    else:
        # 生成 p001 到 p020 的列表
        # items = [f'p{i:03d}' for i in range(1, args.num_purse+1)] # noqa
        items = [f'p{i:03d}' for i in range(args.purse_start_id, args.purse_end_id+1)] # noqa
        # items = ['p012']
        # items = ['p012', 'p015']

    profiles = copy.deepcopy(items)

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(items)
    n = 0
    d_checkin = {}
    d_nft_purchased = {}
    d_nft_limit = {}
    d_usdg = {}
    instParticleTask = ParticleTask()

    while items:
        n += 1
        logger.info('#'*40)
        s_profile = random.choice(items)
        logger.info(f'progress:{n}/{total} [{s_profile}]') # noqa
        items.remove(s_profile)

        args.s_profile = s_profile

        # 切换 IP 后，可能出现异常(与页面的连接已断开)，增加重试
        max_try_except = 3
        for j in range(1, max_try_except+1):
            try:
                if j > 1:
                    logger.info(f'异常重试，当前是第{j}次执行，最多尝试{max_try_except}次 [{s_profile}]') # noqa
                instParticleTask.set_args(args)

                if s_profile in instParticleTask.dic_status:
                    lst_status = instParticleTask.dic_status[s_profile]

                    d_checkin[s_profile] = lst_status[1]
                    d_nft_purchased[s_profile] = lst_status[2]
                    d_nft_limit[s_profile] = lst_status[3]
                    d_usdg[s_profile] = lst_status[4]
                else:
                    lst_status = None

                run_checkin = True
                if lst_status and lst_status[1] == 'DONE':
                    is_checked_in = True
                    run_checkin = False
                    logger.info(f'[{s_profile}] Check-in 已完成')

                run_nft = True
                if lst_status:
                    nft_purchased = int(lst_status[2])
                    nft_limit = int(lst_status[3])
                    if nft_purchased == DEF_NUM_NFT:
                        run_nft = False
                        logger.info(f'[{s_profile}] NFT PURCHASE 已完成')

                if run_checkin or run_nft:
                    # instParticleTask.init_proxy()
                    instParticleTask.initChrome(s_profile)
                    instParticleTask.open_okx()
                    instParticleTask.particle_init()

                    if run_checkin:
                        is_checked_in = instParticleTask.check_in()
                    if run_nft:
                        (nft_purchased, nft_limit) = instParticleTask.particle_nft() # noqa

                    instParticleTask.close()

                    if is_checked_in:
                        d_checkin[s_profile] = 'DONE'
                    else:
                        d_checkin[s_profile] = 'XXXXXXXXXX'
                    d_nft_purchased[s_profile] = nft_purchased
                    d_nft_limit[s_profile] = nft_limit
                    d_usdg[s_profile] = instParticleTask.usdg

                    instParticleTask.dic_status[s_profile] = [
                        s_profile,
                        d_checkin[s_profile],
                        nft_purchased,
                        nft_limit,
                        instParticleTask.usdg
                    ]
                    instParticleTask.status_save()
                else:
                    pass

                break
            except Exception as e:
                logger.info(f'[{s_profile}] An error occurred: {str(e)}')
                if j < max_try_except:
                    time.sleep(5)

        logger.info('Finish')

        if len(items) > 0:
            sleep_time = random.randint(args.sleep_sec_min, args.sleep_sec_max)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)

    if len(DEF_DING_TOKEN) > 0:
        s_info = ''
        for s_profile in profiles:
            s_info += '- {} {} {}/{} ${}\n'.format(
                s_profile,
                d_checkin.get(s_profile, '-'),
                d_nft_purchased.get(s_profile, '-'),
                d_nft_limit.get(s_profile, '-'),
                d_usdg.get(s_profile, '-')
            )
        d_cont = {
            'title': 'Finished',
            'text': (
                '- Checkin NFT and Limit USDG\n'
                '{}\n'
                .format(s_info)
            )
        }
        ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")


if __name__ == '__main__':
    """
    生成 p001 到 p999 的列表
    例如 ['p001', 'p002', 'p003', ...]
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--purse_start_id', required=False, default=1, type=int,
        help='[默认为 1] 首个账号 ID'
    )
    parser.add_argument(
        '--purse_end_id', required=False, default=20, type=int,
        help='[默认为 20] 最后一个账号的 ID'
    )
    parser.add_argument(
        '--sleep_sec_min', required=False, default=3, type=int,
        help='[默认为 3] 每个账号执行完 sleep 的最小时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_max', required=False, default=10, type=int,
        help='[默认为 10] 每个账号执行完 sleep 的最大时长(单位是秒)'
    )
    parser.add_argument(
        '--sleep_sec_at_start', required=False, default=0, type=int,
        help='[默认为 0] 在启动后先 sleep 的时长(单位是秒)'
    )
    parser.add_argument(
        '--profile', required=False, default='',
        help='按指定的 profile 执行，多个用英文逗号分隔'
    )
    args = parser.parse_args()
    main(args)
