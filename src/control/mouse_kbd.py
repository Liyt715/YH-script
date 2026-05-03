import win32gui
import win32con
import win32api
import ctypes
import time
import sys
import os

class MouseController:
    def __init__(self, window_title="异环"):
        """初始化鼠标控制器"""
        self.window_title = window_title
        self.hwnd = None
        
        # 【关键修复】声明进程的 DPI 感知，防止因 Windows 系统 125%/150% 缩放导致前台物理鼠标坐标发生偏移
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

    def find_game_window(self):
        """寻找游戏进程窗口句柄 (和 screen.py 里的逻辑通用)"""
        self.hwnd = win32gui.FindWindow(None, self.window_title)
        
        if self.hwnd == 0:
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    # 改为严格等于，避免匹配到名称包含关键词的其他窗口
                    # if title == self.window_title:
                    if self.window_title in title and title!="异环脚本":
                        self.hwnd = hwnd
            win32gui.EnumWindows(callback, None)
            
        if self.hwnd == 0 or self.hwnd is None:
            self.hwnd = None
            return False
        return True

    def click(self, x, y, button="left"):
        """
        前台物理级点击 (终极杀手锏：100%有效，但会占用真实的鼠标和前台窗口)
        由于游戏屏蔽了后台指令(DirectInput截断)，现已统一采用此方案。
        
        :param x: 窗口内的相对 X 坐标 (整数)
        :param y: 窗口内的相对 Y 坐标 (整数)
        :param button: 'left' (左键) 或 'right' (右键)
        :return: bool 是否点击成功
        """
        if not self.hwnd:
            if not self.find_game_window():
                raise RuntimeError(f"【点击失败】未找到目标窗口 '{self.window_title}'，游戏可能已关闭或最小化。")
        
        try:
            # 1. 把游戏窗口弹到前台
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.1) # 等待窗口切换完成
            
            # 2. 将窗口内的相对坐标 转换为 屏幕绝对坐标
            client_point = (int(x), int(y))
            screen_x, screen_y = win32gui.ClientToScreen(self.hwnd, client_point)
            
            # 3. 移动真实的物理鼠标
            win32api.SetCursorPos((screen_x, screen_y))
            time.sleep(0.05)
            
            # 4. 模拟真实的物理微动开关按下
            if button == "left":
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            elif button == "right":
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                time.sleep(0.05)
                win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            
            print(f"[鼠标控制] 成功进行物理点击坐标: {client_point} -> 屏幕绝对({screen_x}, {screen_y})")
            return True
        except Exception as e:
            raise RuntimeError(f"【点击异常】执行前台点击时报错: {e}")

# ==================== 测试代码 ====================
if __name__ == "__main__":
    import ctypes
    mouse = MouseController("异环")
    # 自动获取管理员权限的魔法代码
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("当前无管理员权限，正在请求 UAC 提权...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        sys.exit()
    
    # 填入你用画图工具看出来的按钮坐标
    test_x, test_y = 50,50
    
    is_success = mouse.click(test_x, test_y, button="left") 
    
    print(f"\n指令发送状态: {is_success}")
    print("测试完毕。")