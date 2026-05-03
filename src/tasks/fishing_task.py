import sys
import os
import time

# 将项目根目录加进系统路径，方便单独运行这个文件进行测试
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.vision.screen import ScreenCapturer
from src.control.mouse_kbd import MouseController
from src.vision.matcher import ImageMatcher
from src.control.keyboard_ctrl import KeyboardController

# 全局常量：钓鱼任务相关的固定按键坐标 (目前为占位示例坐标，需根据实际游戏画面调整)
BTN_POS = {
    "START_FISHING": (1600, 900),      # 抛竿按钮坐标示例
    "PULL_ROD": (1500, 800),           # 拉杆按钮坐标示例
    "EXIT": (50, 50),                  # 左上角退出按钮
}

class FishingTask:
    def __init__(self, window_title="异环"):
        """初始化钓鱼任务对象"""
        self.capturer = ScreenCapturer(window_title)
        self.mouse = MouseController(window_title)
        self.matcher = ImageMatcher()
        self.keyboard = KeyboardController(window_title)
        # 可以按需加入 NumberReader 等其他识别工具

    def run_once(self, logger=None, cnt=0):
        """
        执行一遍单次的钓鱼任务核心逻辑。
        """
        
        if cnt == 1:
            # 这里可以添加对初始钓鱼界面的识别校验
            # similarity = self.matcher.compare_similarity(saved_path, r"assets\images\fishing-start.png")
            pass
        
        # 第一步：获取当前游戏截图
        saved_path = self.execute_screenshot(logger=logger)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fish_F_path = os.path.join(root_dir, "assets", "images", "fish-F.png")
        fish_E_path = os.path.join(root_dir, "assets", "images", "fish-E.png")
        fish_Q_path = os.path.join(root_dir, "assets", "images", "fish-Q.png")
        fish_R_path = os.path.join(root_dir, "assets", "images", "fish-R.png")
        roi= [1350, 900, 1850, 1080] # 右下角钓鱼按钮的 ROI 区域坐标示例 [x1, y1, x2, y2]
        result_F = self.matcher.find_transparent_ui(
            screen_image=saved_path, 
            template_name=fish_F_path, 
            roi_rect=roi,
            threshold=0.8 
        )
        result_E = self.matcher.find_transparent_ui(
            screen_image=saved_path, 
            template_name=fish_E_path, 
            roi_rect=roi,
            threshold=0.8 
        )
        result_Q = self.matcher.find_transparent_ui(
            screen_image=saved_path, 
            template_name=fish_Q_path, 
            roi_rect=roi,
            threshold=0.8 
        )
        result_R = self.matcher.find_transparent_ui(
            screen_image=saved_path, 
            template_name=fish_R_path, 
            roi_rect=roi,
            threshold=0.8 
        )
        if result_F or result_E or result_Q or result_R:
            msg = f"检测到钓鱼按钮，准备执行钓鱼任务！"
            if logger: logger(msg)
            else: print(msg)
        else:
            msg = f"未检测到钓鱼按钮，无法执行钓鱼任务！请检查游戏画面是否正确，或调整模板图片和阈值。"
            raise RuntimeError(msg)
        
        msg_start = f"第 {cnt} 次执行钓鱼任务..."
        if logger: logger(msg_start)
        else: print(msg_start)
        self.keyboard.press_key('f')  # 模拟按下 'F' 键开始钓鱼
        time.sleep(0.5)  # 等待提示出现
        saved_path = self.execute_screenshot(logger=logger)  # 立即截图，检测是否提示鱼饵用完
        roi_bait = [780,500,1150,580] # 鱼饵用完提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
        similarity_bait = self.matcher.compare_similarity(screen_image=saved_path, reference_image="fish-6.png", roi=roi_bait)
        if similarity_bait > 0.8:
            msg_bait = f"检测到鱼饵用完提示，正在自动购买鱼饵..."
            if logger: logger(msg_bait)
            else: print(msg_bait)
            self.keyboard.press_key('r')  # 模拟按下 'R' 键购买鱼饵
            time.sleep(1)
            self.mouse.click(1820, 950)  # 点击到购买上限
            time.sleep(1)
            self.mouse.click(1600, 1030)  # 点击购买
            time.sleep(1)
            save_parh = self.execute_screenshot(logger=logger)  # 再次截图，检测购买结果
            roi_buy = [830, 500, 1100, 580] # 购买结果提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
            similarity_buy = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-8.png", roi=roi_buy)
            if similarity_buy > 0.8:
                msg_buy = f"货币不足，无法购买鱼饵..."
                if logger: logger(msg_buy)
                else: print(msg_buy)
                raise RuntimeError(msg_buy)
            else:
                self.mouse.click(1160, 700) # 点击确认
                time.sleep(2)
                self.mouse.click(950,900)  # 点击确认购买后关闭提示框
                time.sleep(1)
                self.mouse.click(1830,60) # 点击关闭购买界面
                time.sleep(1)
                msg_buy_success = f"已成功购买鱼饵，继续执行钓鱼任务..."
                if logger: logger(msg_buy_success)
                else: print(msg_buy_success)
                self.keyboard.press_key('e') # 按下 'E' 键装备鱼饵
                time.sleep(1)
                self.mouse.click(1170,700) # 点击更换鱼饵
                time.sleep(1)
                self.keyboard.press_key('f')  # 再次按下 'F' 键开始钓鱼

        time.sleep(1)  # 等待钓鱼上钩的提示出现

        saved_path = self.execute_screenshot(logger=logger)  # 再次截图，检测钓鱼状态
        roi_state = [770, 245, 1175, 280] # 钓鱼状态提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
        similarity = self.matcher.compare_similarity(screen_image=saved_path, reference_image="fish-2.png", roi=roi_state)
        pre_time = time.time()
        while similarity < 0.8:  # 如果钓鱼状态提示未出现，继续等待
            time.sleep(0.1)
            saved_path = self.execute_screenshot(logger=logger)
            similarity = self.matcher.compare_similarity(screen_image=saved_path, reference_image="fish-2.png", roi=roi_state)
            if time.time() - pre_time > 10:  # 超过 10 秒还未检测到，认为失败
                raise RuntimeError("钓鱼状态提示长时间未出现，任务执行失败！")
        self.keyboard.press_key('f')  # 继续点击 'F' 键
        """
        开始执行钓鱼溜鱼小游戏的核心逻辑
        """
        if logger: logger(">>> 鱼咬钩了！进入溜鱼模式...")
        else: print(">>> 鱼咬钩了！进入溜鱼模式...")
        bar_roi = [600,60,1325,90] # 钓鱼进度条的 ROI 区域坐标示例 [x1, y1, x2, y2]
        live_screen = self.capturer.grab_screen()
        status = self.matcher.get_fishing_bar_status(live_screen, roi_rect=bar_roi)
        while status is None: 
            live_screen = self.capturer.grab_screen()
            status = self.matcher.get_fishing_bar_status(live_screen, roi_rect=bar_roi)
        while True:
            # 1. 瞬间截取内存画面 (极速)
            live_screen = self.capturer.grab_screen()
            # 2. 获取当前进度条状态
            status = self.matcher.get_fishing_bar_status(live_screen, roi_rect=bar_roi)
            if status is None: #加强一次
                live_screen = self.capturer.grab_screen()
                status = self.matcher.get_fishing_bar_status(live_screen, roi_rect=bar_roi)
            
            if status is None:

                # 如果连续找不到进度条，说明钓鱼可能结束了（成功或失败）
                if logger: logger("未检测到进度条，溜鱼结束。")
                else: print("未检测到进度条，溜鱼结束。")
                break
                
            # 3. 提取坐标信息
            safe_left = status["green_left"]
            safe_right = status["green_right"]
            current_pos = status["yellow_x"]
            
            # ==========================================
            # 4. 核心大脑：根据位置决定按键逻辑
            # ==========================================
            # 这里的逻辑需要根据你游戏的实际操作来写。
            # 假设游戏规则是：按住左键(或A)黄线往左走，按住右键(或D)黄线往右走
            
            # 计算绿条的中心点
            safe_center = (safe_left + safe_right) // 2
            
            if current_pos < safe_center - 10:
                # 如果黄线偏左了，我们需要让它往右走
                if logger: pass
                else: print(f"偏左 ({current_pos})，正在向右拉...")
                # self.mouse.click_down("right") 或者按键盘的 D 键
                self.keyboard.press_key('d')
            elif current_pos > safe_center + 10:
                # 如果黄线偏右了，我们需要让它往左走
                if logger: pass
                else: print(f"偏右 ({current_pos})，正在向左拉...")
                # self.mouse.click_down("left") 或者按键盘的 A 键
                self.keyboard.press_key('a')
                
            else:
                # 处于完美的中心地带，保持不动
                pass 
                
            # 控制一下循环频率，不要让 CPU 100% 满载，0.05秒检查一次足够了
            # time.sleep(0.05)
        
        save_parh = self.execute_screenshot(logger=logger)  # 最后再截图一次，记录结果
        roi_seccess = [840,960,1080,1000] # 钓鱼成功提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
        roi_fail = [850,500,1050,580] # 钓鱼失败提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
        similarity_success = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-4.png", roi=roi_seccess)
        similarity_fail = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-5.png", roi=roi_fail)
        while True:
            if similarity_success > 0.8:
                if logger: logger("钓鱼成功！")
                else: print("钓鱼成功！")
                break
            elif similarity_fail > 0.8:
                if logger: logger("钓鱼失败了！")
                else: print("钓鱼失败了！")
                break
            else:
                # 如果两者都没有检测到，说明可能提示还没出来，继续等待
                time.sleep(0.01)
                save_parh = self.execute_screenshot(logger=logger)
                similarity_success = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-4.png", roi=roi_seccess)
                similarity_fail = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-5.png", roi=roi_fail)

        self.mouse.click(960, 540)  # 点击屏幕中央，关闭结果提示框（示例坐标，需根据实际调整）
        
        # 结束确认处理，比如关闭结算页面等...
        msg_end = f"第 {cnt} 次钓鱼任务执行完毕。"
        if logger: logger(msg_end)
        else: print(msg_end)


    def execute_screenshot(self, logger=None):
        """
        调用 ScreenCapturer 截图并保存。
        如果截图失败，抛出 RuntimeError 异常。
        """
        saved_path = self.capturer.save_screenshot("temp", logger=logger)
        return saved_path

# 测试代码
if __name__ == "__main__":
    import ctypes
    
    # 自动获取管理员权限的魔法代码
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("当前无管理员权限，正在请求 UAC 提权...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        sys.exit()

    task = FishingTask("异环")
    try:
        task.run_once(cnt=1)
    except Exception as e:
        print(f"捕获到异常: {e}")
