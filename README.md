# particle_checkin
Auto complete particle testnetwork check-in and purchase NFT

# venv
```
# 创建新的venv环境
python3 -m venv venv
# 激活环境
source venv/bin/activate
# 退出环境
deactivate
```

# Install
```
pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt -i https://pypi.doubanio.com/simple
```

# Run
```
cd particle_checkin/
cp conf.py.sample conf.py
python mail.py
```

# OKX Plugin
```
1、在 conf.py 设置有头浏览器模式
DEF_USE_HEADLESS = False
2、执行，弹出浏览器
3、手动安装浏览器插件 OKX Wallet
```
