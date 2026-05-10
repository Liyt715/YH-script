import sys
import os
import ctypes

def enable_high_dpi_awareness():
    """强制 Windows 禁用 DPI 虚拟化缩放，获取真实的物理像素分辨率"""
    if sys.platform == "win32":
        try:
            # 第一优先级：Windows 8.1+ (Per-Monitor V1 API)
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # 第二优先级：Windows Vista / 8
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

# 立即执行 DPI 提权（绝对不能放在文件后面）
enable_high_dpi_awareness()

# 彻底关闭 Qt6 底层关于窗口的警告日志输出
os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"

# 注意：Qt6 默认开启了高分屏自适应渲染。不需要强行关闭它的缩放，
# 让它自己去适应 200% 的屏幕即可，这样按钮才不会小得看不见。
# os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"  

# 将项目根目录添加到系统路径，确保能正确导入 src 目录下的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

# ==========================================
# 【全局配置】
# DEBUG_MODE = True  : 开发者模式，保留黑框，方便看 print 和报错闪退信息
# DEBUG_MODE = False : 正式发布模式，隐藏黑框，界面干净
# ==========================================
DEBUG_MODE = True

def main():
    # 创建 Qt 应用程序实例
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 进入应用程序的主事件循环
    sys.exit(app.exec())
    

if __name__ == "__main__":
    # 自动获取管理员权限的魔法代码
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("当前无管理员权限，正在请求 UAC 提权...")
        
        if getattr(sys, 'frozen', False):
            # 如果是 PyInstaller 打包后的 exe 环境
            exe = sys.executable
            # 传递原始启动参数
            params = " ".join(sys.argv[1:])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
        else:
            # 如果是源码开发环境
            if DEBUG_MODE:
                # 调试模式：用原生的 python.exe，保留黑框看日志
                exe = sys.executable 
            else:
                # 发布模式：用 pythonw.exe，隐藏黑框
                exe = sys.executable.replace("python.exe", "pythonw.exe")
                
            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, __file__, None, 1)
        sys.exit()

    # 只有拿到管理员权限后，才会真正启动 UI 界面
    main()