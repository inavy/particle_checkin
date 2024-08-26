import sys # noqa
import logging
import random
import re
import time

from DrissionPage import ChromiumOptions
from DrissionPage import ChromiumPage
from DrissionPage._elements.none_element import NoneElement

from fun_utils import ding_msg

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
from conf import FILENAME_LOG


"""
2024.08.25
1. 基于 drissionpage
https://drissionpage.cn/QandA
2. 当出现 cloudflare 5秒盾 真人验证，需手动点击
3. 一个 IP 每天只能做 20次左右的交互，提示 ip full 时，需要手动更换 IP
4. IP FULL 钉钉告警
5. 支持无头浏览器模式
"""

# 配置日志
s_format = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(
    filename=FILENAME_LOG, level=logging.INFO,
    format=s_format,
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def initChrome(s_profile):
    """
    s_profile: 浏览器数据用户目录名称
    """
    global page
    profile_path = s_profile

    co = ChromiumOptions()

    # 设置本地启动端口
    co.set_local_port(port=DEF_LOCAL_PORT)

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
        page = ChromiumPage(co)

        # logger.info(co.browser_path)

        # page.get('https://pioneer.particle.network/zh-CN/point')
        # page.get('http://DrissionPage.cn')
        # page.quit()
    except Exception as e:
        logger.info(f'Error: {e}')
    finally:
        pass


def open_okx():
    EXTENSION_ID = 'mcohilncbfahbmgdjkbpemcciiolgcge'
    logger.info('Open okx to login ...')
    page.get('chrome-extension://{}/home.html'.format(EXTENSION_ID))

    ele_input = page.ele('@data-testid=okd-input', timeout=2)
    if not isinstance(ele_input, NoneElement):
        logger.info('OKX 输入密码')
        ele_input.input(DEF_PWD)
        logger.info('OKX 登录')
        page.ele('@data-testid=okd-button').click()

    x_path = '//*[@id="home-page-root-element-id"]/div[2]/div'
    balance = page.ele('x:{}'.format(x_path), timeout=2)
    if not isinstance(balance, NoneElement):
        logger.info('账户余额：{}'.format(balance.text))
    else:
        logger.info('okx is invalid! Exit!')
        if DEF_USE_HEADLESS:
            page.quit()
        sys.exit(-1)
    logger.info('okx login success')


def okx_confirm():
    logger.info('准备 OKX Wallet Confirm ...')
    # page.wait.load_start()
    # 当出现 cloudflare 时，勾选
    try:
        button = page.ele('x://*[@id="RlquG0"]/div/label/input')
        logger.info(button.text)
        button.click()
    except: # noqa
        pass

    if len(page.tab_ids) == 2:
        tab_id = page.latest_tab
        tab_new = page.get_tab(tab_id)
        buttons = tab_new.eles('@data-testid=okd-button')
        buttons[-1].click()


def check_ip_full():
    try:
        toastify = page.ele('x://*[@id="1"]/div[1]/div[2]', timeout=2).text
    except: # noqa
        toastify = ''
    if len(toastify) > 0:
        logger.info('toastify={}'.format(toastify))

    if toastify == DEF_IP_FULL:
        if len(DEF_DING_TOKEN) > 0:
            d_cont = {
                'title': 'ip is full',
                'text': (
                    '- The number of times this ip sent today is full\n'
                    '- please try again tomorrow\n'
                )
            }
            ding_msg(d_cont, DEF_DING_TOKEN, msgtype="markdown")

        logger.info('ERROR! IP is full')
        page.quit()
        # time.sleep(60)
        return True
    else:
        return False


def check_in():
    for i in range(DEF_NUM_TRY_CHECKIN):
        logger.info('check_in try_i={}'.format(i+1))
        page.get('https://pioneer.particle.network/zh-CN/point')

        logger.info('准备 CHECK-IN ...')
        # page.wait.load_start()

        x_path = '//*[@id="portal"]/div[2]/div[2]/div[1]/div/div[4]/div[4]/button/div[1]' # noqa
        page.wait.eles_loaded('x:{}'.format(x_path))
        logger.info('sleep {} seconds...'.format(i+1))
        time.sleep(i+1)
        button = page.ele('x:{}'.format(x_path))

        if button.text == 'Checked in':
            logger.info('Oh! Check-in is already done before!')
            return

        if button.text == 'Check-in':
            button.click()

        # SEND TRANSACTION 窗口
        x_path = '/html/body/div[4]/div/div[2]/div/div/div[1]'
        button = page.ele('x:{}'.format(x_path), timeout=2)
        if isinstance(button, NoneElement):
            logger.info('没有 SEND TRANSACTION 窗口，从头重试 ...')
            continue

        logger.info('准备点击 CONFIRM 按钮')
        x_path = '//html/body/div[4]/div/div[2]/div/div/div[2]/div[4]/div[2]/button/div[1]' # noqa
        button = page.ele('x:{}'.format(x_path), timeout=10)
        if isinstance(button, NoneElement):
            logger.info('没有 CONFIRM 按钮，从头重试 ...')
            continue
        button.click()

        logger.info('准备 OKX CONFIRM')
        okx_confirm()
        if check_ip_full():
            if DEF_USE_HEADLESS:
                page.quit()
            sys.exit(-1)
        logger.info('Check-in is Finished!')


def activate():
    """
    # noqa
    激活后回到 PURCHASE 页面
    # DEF_URL_ACTIVATE = 'https://pioneer.particle.network/zh-CN/accountAnimation'
    # DEF_URL_SIGNUP = 'https://pioneer.particle.network/zh-CN/signup'
    """
    # page.wait.load_start()
    logger.info('Current url: {}'.format(page.url))

    try:
        # 图片
        x_path = '/html/body/div[1]/div[1]/div/div[1]/div[3]/div[3]/img' # noqa
        page.wait.eles_loaded('x:{}'.format(x_path))

        # DrissionPage.errors.NoRectError: 该元素没有位置及大小
        time.sleep(1)

        button = page.ele('x:{}'.format(x_path)) # noqa
        if isinstance(button, NoneElement):
            return False
        logger.info('CLICK TO ACTIVATE')
        if DEF_DEBUG:
            print(page.tab_ids)
        button.click()
    except: # noqa
        logger.info('没有 CLICK TO ACTIVATE')
        # return False

    logger.info('Current url: {}'.format(page.url))

    # CLICK TO LAUNCH
    logger.info('CLICK TO LAUNCH ...')
    try:
        button = page.ele('x:/html/body/div[1]/div[1]/div/div[1]/a/div')
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
        button = page.ele('x://*[@id="home"]/div/div[1]/div/div[2]/a/div[1]')
        logger.info('button.text={}'.format(button.text))
        if button.text == 'LAUNCH':
            button.click()
            logger.info('LAUNCH SUCCESS')
            return True
    except: # noqa
        logger.info('没有 LAUNCH')
        return False

    return True


def check_nft_num():
    """
    返回值 num_ret
    [1, 5]
    第一个数: 今天成功购买的 NFT 数量
    第二个数: 今天计算积分的 NFT 数量，超出该数量不算积分
    """
    num_ret = [0, 0]

    for i in range(DEF_NUM_TRY_PURCHASE_NFT):
        logger.info('check_nft_num try_i={}'.format(i+1))
        page.get('https://pioneer.particle.network/zh-CN/point')

        # logger.info('即将刷新页面 {}'.format(page.url))
        page.refresh()

        x_path = '//*[@id="portal"]/div[2]/div[2]/div[4]/div/div[4]/div/div'
        page.actions.move_to('x:{}'.format(x_path))
        page.wait.eles_loaded('x:{}'.format(x_path))
        button = page.ele('x:{}'.format(x_path), timeout=2)
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


def purchase_nft():
    """
    返回值 s_msg
    """
    s_msg = DEF_MSG_FAIL
    for i in range(DEF_NUM_TRY_PURCHASE_NFT):
        logger.info('purchase_nft try_i={}'.format(i+1))
        page.get('https://pioneer.particle.network/zh-CN/crossChainNFT')

        logger.info('即将刷新页面 {}'.format(page.url))
        page.refresh()

        logger.info('准备在 crossChainNFT 页面点击 PURCHASE 按钮 ...')
        time.sleep(5)
        button = page.ele('x://*[@id="content-wrapper"]/div/div[2]/div[1]/div[3]/div[2]/div[4]/button/div[1]') # noqa
        if button and button.text == 'Purchase':
            button.click()
        else:
            logger.info('没有 PURCHASE 按钮，重新开始')
            continue

        logger.info('准备选中 USDG 复选框 ...')
        time.sleep(5)
        buttons = page.eles('.:polygon-small mb-3 flex cursor-pointer')
        if len(buttons) >= 1:
            buttons[0].click()
        else:
            logger.info('没有 USDG 选项，重新开始')
            continue

        logger.info('准备 Click Next BUTTON ...')
        x_path = '/html/body/div[4]/div/div[2]/div/div/div[2]/div[6]/button/div[1]' # noqa
        button = page.ele('x:{}'.format(x_path))
        if button.text == 'Next':
            time.sleep(1)
            button.click()
        else:
            logger.info('没有 Next 按钮，重新开始')
            continue

        logger.info('准备在 NETWORK FEE 弹窗点击 PURCHASE 按钮 ...')
        x_path = '/html/body/div[4]/div/div[2]/div/div/button/div[1]'
        button = page.ele('x:{}'.format(x_path))
        if isinstance(button, NoneElement):
            logger.info('没有 NETWORK FEE 弹窗，重新开始')
            continue
        if button.text == 'Purchase':
            time.sleep(1)
            button.click()
        else:
            logger.info('没有 PURCHASE 按钮，重新开始')
            continue

        # 此处可能会出现 CLOUDFLARE 5秒盾，留点时间
        time.sleep(3)

        okx_confirm()
        if check_ip_full():
            s_msg = DEF_MSG_IP_FULL
            break

        logger.info('正在确认 SUCCESSFUL 弹窗 ...')
        # 出现 SUCCESSFUL 弹窗，需要等待几秒
        time.sleep(3)
        x_path = '/html/body/div[4]/div/div[2]/div/div/div[1]'
        page.wait.eles_loaded('x:{}'.format(x_path), timeout=2)
        button = page.ele('x:{}'.format(x_path), timeout=2)
        if isinstance(button, NoneElement):
            logger.info('没有 SUCCESSFUL 弹窗，重新开始')
            continue
        else:
            logger.info('button.text:{}'.format(button.text))
            if button.text.startswith('SUCCESSFULLY'):
                logger.info('有 SUCCESSFUL 弹窗')
                # 弹窗右上角的 ×
                x_path = '/html/body/div[4]/div/div[2]/div/button'
                try:
                    page.ele('x:{}'.format(x_path)).click()
                    logger.info('SUCCESSFUL 弹窗，关闭成功')
                except: # noqa
                    logger.info('SUCCESSFUL 弹窗，关闭失败')
                    pass
            else:
                logger.info('Purchase Failed，重新开始 ...')
                continue

        s_msg = DEF_MSG_SUCCESS
        break

    if s_msg == DEF_MSG_FAIL:
        s_error = 'PURCHASE_NFT 连续{}次失败'.format(DEF_NUM_TRY_PURCHASE_NFT)
        logger.info(s_error)

    return s_msg


def particle_login():
    try:
        # 首次登录有弹窗，点击 START
        logger.info('正在确认是否有 START 弹窗 ...')
        time.sleep(2)
        x_path = '/html/body/div[1]/button'
        page.wait.eles_loaded('x:{}'.format(x_path))
        button = page.ele('x:{}'.format(x_path), timeout=2)
        if not isinstance(button, NoneElement):
            logger.info('点击 START')
            button.click()
        else:
            logger.info('没有 START 弹窗')
    except: # noqa
        pass

    button = page.ele('.polygon-btn-text')
    logger.info('正在根据按钮[{}]确认登录状态 ...'.format(button.text))
    if 'JOINNOW' == button.text:
        logger.info('点击 JOINNOW 按钮 ...')
        button.click()

        # 选择登录的钱包
        x_path = '/html/body/div[1]/div[1]/div/div[1]/div[4]/div[3]/div[1]/button' # noqa
        button = page.ele('x:{}'.format(x_path))
        logger.info('正在点击 OKX WALLET 连接 OKX 钱包 ...')
        button.click()

        # OKX Wallet 连接
        logger.info('OKX Wallet 连接')
        # 需要等待弹窗加载完成
        page.wait.load_start()
        if DEF_DEBUG:
            print(page.tab_ids)
        if len(page.tab_ids) == 2:
            try:
                tab_id = page.latest_tab
                tab_new = page.get_tab(tab_id)
                button = tab_new.ele('x://*[@id="app"]/div/div/div/div/div[5]/div[2]/button[2]') # noqa
                logger.info('{}'.format(button.text))
                button.click()
            except: # noqa
                pass

        # OKX Wallet 请求签名
        logger.info('OKX Wallet 请求签名')
        page.wait.load_start()
        if DEF_DEBUG:
            print(page.tab_ids)
        if len(page.tab_ids) == 2:
            try:
                tab_id = page.latest_tab
                tab_new = page.get_tab(tab_id)
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
            if page.ele('x:{}'.format(x_path), timeout=2).click():
                logger.info('成功点击 LAUNCH')
        except: # noqa
            pass


def particle_init():
    """
    登录及校验是否登录成功
    """
    page.get('https://pioneer.particle.network/zh-CN/point')

    for i in range(10):
        logger.info('Page Login try_i={}'.format(i+1))
        particle_login()

        logger.info('检查是否登录成功 ...')
        time.sleep(1)

        # 这是已登录时的 xpath
        x_path = '//*[@id="navbar"]/header/ul[3]/li/div/button'
        page.wait.eles_loaded('x:{}'.format(x_path))
        button = page.ele('x:{}'.format(x_path), timeout=2)
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
        page.wait.eles_loaded('x:{}'.format(x_path))
        button = page.ele('x:{}'.format(x_path), timeout=2)
        if isinstance(button, NoneElement):
            logger.info('没有获取到登录状态，从头重试 ...')
            continue

        if 'JOINNOW' == button.text:
            logger.info('页面未登录，重试 ...')
            continue
        else:
            logger.info('页面已成功登录')
            break


def particle_nft():
    logger.info('准备 Purchase NFT ...')
    for i in range(DEF_NUM_NFT):
        logger.info('#'*30)
        logger.info('i={}'.format(i+1))
        num_nft = check_nft_num()
        if num_nft[1] > 0 and num_nft[0] >= DEF_NUM_NFT:
            break
        if DEF_MSG_IP_FULL == purchase_nft():
            break
        time.sleep(2)


if __name__ == '__main__':
    """
    生成 p001 到 p020 的列表
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    # 生成 p001 到 p020 的列表
    items = [f"p{i:03d}" for i in range(1, 21)] # noqa
    # items = ['p001']

    # 每次随机取一个出来，并从原列表中删除，直到原列表为空
    total = len(items)
    n = 0
    while items:
        n += 1
        logger.info('#'*60)
        logger.info('progress:{}/{}'.format(n, total))
        s_profile = random.choice(items)
        logger.info(s_profile)
        items.remove(s_profile)

        initChrome(s_profile)
        open_okx()
        particle_init()
        check_in()
        particle_nft()
        logger.info('Finish')
        page.quit()

        if len(items) > 0:
            # sleep_time = random.randint(1*60, 10*60)
            sleep_time = random.randint(10, 30)
            if sleep_time > 60:
                logger.info('sleep {} minutes ...'.format(int(sleep_time/60)))
            else:
                logger.info('sleep {} seconds ...'.format(int(sleep_time)))
            time.sleep(sleep_time)