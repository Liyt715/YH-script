# 🎮 异环自动化辅助脚本

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) 
[![PySide6](https://img.shields.io/badge/PySide6-GUI-green)](https://pypi.org/project/PySide6/) 
[![OpenCV](https://img.shields.io/badge/OpenCV-Vision-red)](https://opencv.org/)

一款基于 **Python + OpenCV + PySide6** 构建的《异环》Windows 桌面端智能辅助工具。通过高级计算机视觉（CV）技术实时读取游戏画面，并利用 Windows 原生 API 模拟真实的键鼠操作，实现游戏内特定日常玩法的全自动挂机。

**这个脚本是我用来学习写的（部分手搓部分AI），可能有很多bug**

🚨 **声明：本工具仅供编程学习与技术研究使用，请勿用于商业用途或破坏游戏公平性。**

## ✨ 核心功能 (Features)

目前主要包含在图形界面（GUI）中可选的两大自动化任务模块：

*   🎣 **全自动钓鱼 (Auto Fishing)**
    *    注意事项：先在钓鱼商店选中用鱼鳞币买的万能鱼饵，然后目前还没做没有鱼鳞币就自动卖鱼的功能。
    *   【智能抛竿】与【咬钩抓取】：通过像素级图像比对与透明度分析，毫秒级响应鱼儿咬钩（基于 F / E / Q / R 等快捷键图标状态监测）。
    *   【动态进度条溜鱼】：基于 OpenCV 颜色特征追踪钓鱼进度条的“安全绿区”与“当前黄块”，实时动态下发 `A` 或 `D` 的物理按键指令进行左右拉扯保持平衡。
    *   【智能结算】：自动识别“钓鱼成功”与“钓鱼失败”等结果面板，并关闭结算弹窗准备下一次抛竿。
    *   支持模式：无限 / 限制挂机次数。

*   🀄 **全自动搓麻将 (Auto Mahjong)**
    *   从左至右点击角色槽自动开始备战。
    *   【视觉发牌与高亮识别】：利用图像提取快速抓取麻将牌面区域中的白边高亮提示，辅助点击。
    *   全自动检测并执行 胡 / 碰 / 出 等核心操作以及读取剩余牌数，直至对局结束。
    *   支持模式：无限 / 限制挂机次数。


## ⚙️ 入门指引 (Getting Started)

### 1. 准备环境
确保你熟悉 Python 3.10+。在根目录安装好依赖：
```bash
pip install -r requirements.txt
```
*(主要包含: PySide6, opencv-python, numpy, pypiwin32 等)*

### 2. 启动脚本
**务必在根目录**使用解释器启动 `main.py` (脚本自带自动提权提示)：
```bash
python main.py
```

### 3. 开始挂机
*   先进入游戏，把画面设置为 1920*1080窗口。
*   把你的角色贴近钓鱼点或者麻将桌。
*   主界面左侧列表选择你要挂机的具体业务类型；在中栏配置无限死循环，或者手动填入需要执行的次数（防止挂机太久）。
*   点击底部的【启动任务】。双手拿开，在右侧实时流日志下观察战果！运行中产生过的截图会集中存放在 temp 夹内便于 Debug。

## 📂 项目模块分布 (Structure)

```text
├── main.py                     # 全局入口与 Qt 初始化、提权验证
├── Project Structure.md        # 项目结构梳理文档
├── README.md                   # 说明文档
├── requirements.txt            # 项目运行环境依赖
├── assets/                     # 静态资源存放目录
│   ├── images/                 # 图片资源 (如待匹配的模板图像等)
│   └── ui/                     # UI相关的静态资源或配置
├── config/                     # 本地历史设置或配置文件留存
│   └── settings.json           # 本地设置文件
├── logs/                       # 供 GUI 一键导出的历史操作全文本日志
├── src/                        # 核心源代码目录
│   ├── control/                # 【控制层】键盘、鼠标信号底层驱动库
│   │   ├── keyboard_ctrl.py
│   │   └── mouse_kbd.py
│   ├── tasks/                  # 【逻辑池】串联所有操作的业务执行层
│   │   ├── fishing_task.py     
│   │   └── majiang_task.py   
│   ├── test/                   # 测试脚本文件
│   │   ├── test-fish-bar.py
│   │   ├── test-fish.py
│   │   └── test-roi.py
│   ├── ui/                     # 【交互层】PySide6 驱动的视图组件与线程通信
│   │   └── main_window.py
│   └── vision/                 # 【天眼视觉】纯图形数字解析的算法核心模块
│       ├── matcher.py          # 基于不同算子的找图、读条、提取框中心等算法集合
│       ├── number.py           # 专门识别并在复杂杂图里读取残局数字(基于数字图)
│       └── screen.py           # 高并发、避开遮盖的窗口缓冲流抓取函数
└── temp/                       # 自动存放当次生命周期内的临时抓点图或匹配识别图
```