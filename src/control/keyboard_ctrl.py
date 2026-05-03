import time
import ctypes
import win32gui
import win32con

# 常用虚拟键码映射表 (VK_CODE)
VK_CODE = {
    'backspace': 0x08,
    'tab': 0x09,
    'enter': 0x0D,
    'shift': 0x10,
    'ctrl': 0x11,
    'alt': 0x12,
    'esc': 0x1B,
    'space': 0x20,
    'left': 0x25,
    'up': 0x26,
    'right': 0x27,
    'down': 0x28,
    'w': 0x57,
    'a': 0x41,
    's': 0x53,
    'd': 0x44,
    'e': 0x45,
    'f': 0x46,
    'q': 0x51,
    'r': 0x52,
    # 可根据需要继续补充虚拟键码
}

class KeyboardController:
    def __init__(self, window_title="异环"):
        """初始化键盘控制器"""
        self.window_title = window_title
        self.hwnd = None

    def find_game_window(self):
        """寻找游戏进程窗口句柄"""
        self.hwnd = win32gui.FindWindow(None, self.window_title)
        
        if self.hwnd == 0:
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if self.window_title in title and title != "异环脚本":
                        self.hwnd = hwnd
            win32gui.EnumWindows(callback, None)
            
        if self.hwnd == 0 or self.hwnd is None:
            self.hwnd = None
            return False
        return True

    def press_key(self, key_name, duration=0.1):
        """
        模拟按下单个按键
        :param key_name: 按键名称（例如 'w', 'enter', 'space'）
        :param duration: 按住的时间（秒）
        """
        if not self.hwnd:
            if not self.find_game_window():
                raise RuntimeError(f"【键盘异常】未找到目标窗口 '{self.window_title}'，游戏可能已关闭或最小化。")
                
        try:
            key_lower = key_name.lower()
            if key_lower not in VK_CODE:
                raise ValueError(f"不支持的按键: '{key_name}'，请检查按键名称是否在支持列表中。")
            
            vk = VK_CODE[key_lower]
            
            # 把游戏窗口弹到前台获得焦点（因为 keybd_event 是全局物理级的，窗口必须在前台）
            if win32gui.GetForegroundWindow() != self.hwnd:
                win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(0.5) # 初次将游戏切到前台时，需要更长的等待时间让系统完成焦点转移
            else:
                time.sleep(0.05) # 已经是在前台的话，微小延迟即可
                
            # 很多3D游戏(如UE/Unity引擎)屏蔽了没有硬件扫描码的虚拟按键！
            # 我们需要把虚拟键码映射为真实的物理硬件扫描码 (bScan)
            scan_code = ctypes.windll.user32.MapVirtualKeyA(vk, 0)
            
            # 按下按键 (0x0008 代表 KEYEVENTF_EXTENDEDKEY)
            ctypes.windll.user32.keybd_event(vk, scan_code, 0, 0)
            time.sleep(duration)
            # 释放按键 (2 代表 KEYEVENTF_KEYUP)
            ctypes.windll.user32.keybd_event(vk, scan_code, 2, 0)
            
        except ValueError as ve:
            # 捕获已知参数错误，继续向上抛出，以便上层的 try-except 可以记录到 UI 日志
            raise RuntimeError(f"键盘模拟参数错误: {str(ve)}")
        except Exception as e:
            # 捕获未知的底层系统调用异常，继续向上抛出
            raise RuntimeError(f"键盘模拟底层异常: {str(e)}")

if __name__ == "__main__":
    import sys
    # 自动获取管理员权限的魔法代码（为了切窗口和键盘注入通常需要提权）
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("当前无管理员权限，正在请求 UAC 提权...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        time.sleep(2)
        sys.exit()

    # 测试代码
    kbd = KeyboardController(window_title="异环")
    try:
        print("准备测试按键 'space'，请不要操作鼠标键盘...")
        time.sleep(1)
        kbd.press_key('space')
        print("按键模拟成功")
        time.sleep(1)
        print("准备测试按键 'f'...")
        kbd.press_key('f')
    except RuntimeError as e:
        print(f"成功捕捉到异常输出: {e}")
        
    input("\n按回车键退出...")
