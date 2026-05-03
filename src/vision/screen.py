import cv2
import numpy as np
import win32gui
import win32ui
import win32con
import ctypes
import os
import time
import sys
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.control.mouse_kbd import MouseController
from src.vision.matcher import ImageMatcher

# 强制开启 DPI 感知，防止因 Windows 缩放（比如 125%, 150%）导致取到的窗口尺寸是不准确的“逻辑像素”，从而截断图像
try:
    ctypes.windll.user32.SetProcessDPIAware()
except AttributeError:
    pass

class ScreenCapturer:
    def __init__(self, window_title="异环"):
        """初始化截图器
        :param window_title: 游戏窗口的标题名称
        """
        self.window_title = window_title
        self.matcher = ImageMatcher()
        self.mouse = MouseController()
        self.hwnd = None


    def find_game_window(self):
        """寻找游戏进程窗口句柄 (HWND)"""
        # 第一种方法：精确匹配
        self.hwnd = win32gui.FindWindow(None, self.window_title)
        
        # 如果精确匹配失败，尝试进行模糊匹配（包含该字符串即可）
        if self.hwnd == 0:
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if self.window_title in title:
                        self.hwnd = hwnd
            win32gui.EnumWindows(callback, None)
            
        if self.hwnd == 0 or self.hwnd is None:
            self.hwnd = None
            return False
        return True

    def grab_screen(self):
        """
        核心截屏方法：直接从显存/系统内存提取窗口画面。
        支持窗口被遮盖时截图（游戏不能被最小化）。
        返回: OpenCV (BGR) 图像数组阵列，若未找到窗口返回 None
        """
        if not self.hwnd:
            if not self.find_game_window():
                return None

        # 获取窗口核心客户区的大小 (不包含标题栏和多余边框的纯游戏画面)
        left, top, right, bot = win32gui.GetClientRect(self.hwnd)
        w = right - left
        h = bot - top
        
        if w == 0 or h == 0:
            return None

        # 获取窗口设备上下文 (DC)
        hwndDC = win32gui.GetWindowDC(self.hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # 开辟一段内存空间作为兼容位图
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        # 调用系统底层 API 绘图到内存中
        # PrintWindow 的第3个参数填 3 (PW_RENDERFULLCONTENT)，针对 Win10+ 的硬件加速(Dx/Vulkan)游戏非常有效
        result = ctypes.windll.user32.PrintWindow(self.hwnd, saveDC.GetSafeHdc(), 3)

        img = None
        if result == 1:
            # 提取图像数据，转换成 numpy 数组 (OpenCV 处理的标准格式)
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            img = np.frombuffer(bmpstr, dtype='uint8')
            img.shape = (bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4)
            # 原本是 BGRA 格式，抛弃透明(A)通道转为 BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # 内存释放，防止内存泄漏造成游戏或脚本卡死（极其重要）
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwndDC)

        return img

    def save_screenshot(self, save_dir="temp",logger=None):
        """
        截取当前画面并保存到指定的临时文件夹中。
        文件将以当前时间戳命名。
        """
        img = self.grab_screen()
        if img is None:
            raise RuntimeError(f"截图失败！请检查 '{self.window_title}' 是否运行且未最小化。")
        
        # 将相对路径自动转换为基于项目根目录的绝对路径，防止因启动位置不同产生多份零散 temp 文件夹
        if not os.path.isabs(save_dir):
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            save_dir = os.path.join(root_dir, save_dir)
        
        # 确保保存目录存在，如果不存在则自动创建
        os.makedirs(save_dir, exist_ok=True)
        
        # 按时间生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(save_dir, filename)
        
        # 使用 OpenCV 保存图片
        cv2.imwrite(filepath, img)

        my_roi = [750, 220, 1200, 820]
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        yueka_img_path = os.path.join(root_dir, "assets", "images", "yueka.png")
        
        similarity = self.matcher.compare_similarity(filepath, yueka_img_path, roi=my_roi)
        if(similarity > 0.8):
            msg ="相似度为 {:.2f}".format(similarity)
            self.mouse.click(960,940) # 点击月卡界面
            time.sleep(5)
            self.mouse.click(960,540) # 再次点击
            if logger:
                logger(f"检测到月卡界面，{msg}。已自动点击进入。请确认任务是否继续进行。")
            else:
                print(f"检测到月卡界面，{msg}。已自动点击进入。请确认任务是否继续进行。")
        
        return filepath

if __name__ == "__main__":
    import ctypes
    import sys
    # 自动获取管理员权限的魔法代码
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("当前无管理员权限，正在请求 UAC 提权...")
        # 使用 python.exe 启动，保留控制台黑框以便查看输出
        exe = sys.executable
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, __file__, None, 1)
        time.sleep(2)
        sys.exit()

    capturer = ScreenCapturer()
    try:
        saved_path = capturer.save_screenshot(logger=print)
        print(f"截图已保存到: {saved_path}")
    except RuntimeError as e:
        print(str(e))
        