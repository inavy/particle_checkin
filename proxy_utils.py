import sys
import time
import pyautogui as pg
import screeninfo
import argparse

"""
pip install pyautogui
pip install screeninfo
"""

from conf import DEF_PROXY_LIST
from conf import DEF_SCREEN_WIDTH
from conf import DEF_SCREEN_HEIGHT
from conf import DEF_HEIGHT_ITEM
from conf import DEF_ICON_XY
from conf import DEF_START_XY
from conf import DEF_PROXY_XY


def get_position():
    # 获取所有屏幕的尺寸和位置
    screens = screeninfo.get_monitors()

    # 打印屏幕数量
    print(f'当前连接的显示器数量为：{len(screens)}')

    for i in range(len(screens)):
        print(screens[i])

    try:
        while True:
            # 获取当前鼠标的位置
            x, y = pg.position()
            # 打印鼠标的X和Y坐标
            print(f'鼠标位置: ({x}, {y})', end='\r') # noqa
            # 稍微等待一下，避免输出太快
            time.sleep(0.1)
    except KeyboardInterrupt:
        print('\n程序已终止。')


def get_proxy_xy():
    """
    Return: [[proxy_name, x, y], [proxy_name, x, y]]
    """
    lst_proxy_xy = []
    start_x = DEF_START_XY[0]
    start_y = DEF_START_XY[1]
    for i in range(len(DEF_PROXY_LIST)):
        x = start_x
        y = start_y + DEF_HEIGHT_ITEM * i
        proxy_xy = [DEF_PROXY_LIST[i], x, y]
        lst_proxy_xy.append(proxy_xy)

    return lst_proxy_xy


def change_proxy(black_list=[]):
    """
    black_list: proxy_name black list
    """
    ret_proxy_name = ''

    # 获取屏幕尺寸
    # 元组类型的返回值
    screen_width, screen_height = pg.size()
    # 获取屏幕宽高
    # print("屏幕宽度:", screen_width)
    # print("屏幕高度:", screen_height)

    if screen_width != DEF_SCREEN_WIDTH or screen_height != DEF_SCREEN_HEIGHT:
        return ret_proxy_name

    # 鼠标移动速度
    move_speed_sec = 0.5

    lst_proxy_xy = get_proxy_xy()

    for (s_proxy, x, y) in lst_proxy_xy:
        if s_proxy in black_list:
            continue
        # icon_clashx
        pg.moveTo(DEF_ICON_XY[0], DEF_ICON_XY[1], duration=move_speed_sec)
        time.sleep(1)
        pg.click()

        # proxy item
        pg.moveTo(DEF_PROXY_XY[0], DEF_PROXY_XY[1], duration=move_speed_sec)
        time.sleep(1)
        pg.click()

        pg.moveTo(x, y, duration=move_speed_sec)
        time.sleep(1)
        pg.click()
        ret_proxy_name = s_proxy

        break
    return ret_proxy_name


def main(args):
    """
    time.sleep(5)
    # pic = pg.screenshot(region=[695, 430, 385, 20])
    pic = pg.screenshot()
    pic.save('proxy_using.png')
    sys.exit(-1)
    """

    if args.show_position:
        get_position()
    elif args.change_proxy:
        change_proxy()
    else:
        print('Usage: python {} -h'.format(sys.argv[0]))


if __name__ == '__main__':
    """
    生成 p001 到 p020 的列表
    每次随机取一个出来，并从原列表中删除，直到原列表为空
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--show_position', required=False, action='store_true',
        help='显示鼠标在屏幕上的坐标'
    )
    parser.add_argument(
        '--change_proxy', required=False, action='store_true',
        help='选择 proxy'
    )
    args = parser.parse_args()
    main(args)
