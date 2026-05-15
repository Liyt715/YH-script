import sys
import os
import time
import cv2

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
        self.consecutive_failures = 0  # 新增：连续异常计数器
        # 可以按需加入 NumberReader 等其他识别工具

    def run_once(self, logger=None, cnt=0, check_stop=None):
        """
        执行一遍单次的钓鱼任务核心逻辑。
        """
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.current_temp_dir = os.path.join(root_dir, "temp", f"fishing_{cnt}")
        self.current_cnt = cnt
        import shutil
        if os.path.exists(self.current_temp_dir):
            shutil.rmtree(self.current_temp_dir)
        os.makedirs(self.current_temp_dir, exist_ok=True)
        
        self.slip_records = []
        try:
            self._run_once_impl(logger, cnt, root_dir, check_stop)
            self.consecutive_failures = 0  # 单次执行成功，重置计数器
        except Exception as e:
            if "USER_STOPPED" in str(e): #or "未检测到钓鱼按钮" in str(e) or "无法购买鱼饵" in str(e)
                if os.path.exists(self.current_temp_dir):
                    shutil.rmtree(self.current_temp_dir, ignore_errors=True)
                raise e
            
            self.consecutive_failures += 1  # 发生非用户主动停止的异常，计数器加 1

            # 发生异常时，检查有没有未落盘的内存截图，有则先保存下来
            if hasattr(self, 'slip_records') and self.slip_records:
                if logger: logger("发生异常，正在保存溜鱼期间可能遗漏的暂存截图...")
                else: print("发生异常，正在保存溜鱼期间可能遗漏的暂存截图...")
                import concurrent.futures
                def _save_img(item):
                    fname, f = item
                    if f is not None and getattr(f, 'size', 0) > 0:
                        cv2.imencode('.png', f)[1].tofile(os.path.join(self.current_temp_dir, fname))
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.map(_save_img, self.slip_records)
                self.slip_records.clear()
                
            import shutil
            import re
            error_dir = os.path.join(root_dir, "error")
            os.makedirs(error_dir, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            error_name = str(e)
            error_name = re.sub(r'[\\/*?:"<>|]', "", error_name)[:30].strip('. ')
            if not error_name:
                error_name = type(e).__name__
            error_folder_path = os.path.join(error_dir, f"{timestamp}_{error_name}")
            if os.path.exists(self.current_temp_dir):
                shutil.copytree(self.current_temp_dir, error_folder_path)
            if logger: logger(f"第 {cnt} 次钓鱼发生异常，已跳过。文件夹已复制至: {error_folder_path}")
            else: print(f"第 {cnt} 次钓鱼发生异常，已跳过。文件夹已复制至: {error_folder_path}")
            
            # --- 新增的连续异常熔断机制 ---
            if self.consecutive_failures >= 10:
                msg_err = f"警告：已经连续异常 {self.consecutive_failures} 次，为防止死循环，强制终止主进程！"
                if logger: logger(msg_err)
                else: print(msg_err)
                self.consecutive_failures = 0  # 重新抛出异常前重置计数，防止下次启动受影响
                raise RuntimeError(msg_err)
            
            # 不抛出异常 (raise e)，让主线程可以继续执行下一次抓取
    
    def smart_sleep(self,seconds, check_stop=None):
        """将大块睡眠切碎成 0.05 秒的小块，每次醒来都检查一下是不是被用户强停了"""
        end_time = time.time() + seconds
        while time.time() < end_time:
            if check_stop: 
                check_stop() # 如果用户点了停止，这里会瞬间抛出异常停止函数！
            time.sleep(0.05)
    
    def begin_fishing(self, logger=None):
        saved_path = self.execute_screenshot(logger=logger)
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        fish_F_path = os.path.join(root_dir, "assets", "images", "fish-F.png")
        fish_E_path = os.path.join(root_dir, "assets", "images", "fish-E.png")
        fish_Q_path = os.path.join(root_dir, "assets", "images", "fish-Q.png")
        fish_R_path = os.path.join(root_dir, "assets", "images", "fish-R.png")
        roi= [1350, 900, 1850, 1080] # 右下角钓鱼按钮的 ROI 区域坐标示例 [x1, y1, x2, y2]
        result_F = self.matcher.find_transparent_ui(
            screen_image=saved_path, template_name=fish_F_path, roi_rect=roi,threshold=0.8 
        )
        result_E = self.matcher.find_transparent_ui(
            screen_image=saved_path, template_name=fish_E_path, roi_rect=roi,threshold=0.8 
        )
        result_Q = self.matcher.find_transparent_ui(
            screen_image=saved_path, template_name=fish_Q_path, roi_rect=roi,threshold=0.8 
        )
        result_R = self.matcher.find_transparent_ui(
            screen_image=saved_path, template_name=fish_R_path, roi_rect=roi,threshold=0.8 
        )
        if result_F or result_E or result_Q or result_R:return True
        else:return False

    def buy_fish(self, logger=None, check_stop=None):
        self.keyboard.press_key('r')  # 模拟按下 'R' 键购买鱼饵
        self.smart_sleep(1, check_stop)
        save_parh_yuer = self.execute_screenshot(logger=logger)
        yuer_xy=self.matcher.find_template(save_parh_yuer,"yuer.png",roi=[50,120,650,850])
        if yuer_xy is None:
            self.mouse.click(1830,60) # 点击关闭购买界面
            msg_yuer = f"未检测到万能鱼饵选项，无法自动购买鱼饵！请检查模板图片和阈值。"
            raise RuntimeError(msg_yuer)
        self.mouse.click(yuer_xy[0],yuer_xy[1])  # 选择万能鱼饵
        if logger: logger("已识别到万能鱼饵，位置为: ({}, {})，正在点击购买...".format(yuer_xy[0], yuer_xy[1]))
        else: print("已识别到万能鱼饵，位置为: ({}, {})，正在点击购买...".format(yuer_xy[0], yuer_xy[1]))
        self.smart_sleep(1, check_stop)
        self.mouse.click(1820, 950)  # 点击到购买上限
        self.smart_sleep(1, check_stop)
        self.mouse.click(1600, 1030)  # 点击购买
        self.smart_sleep(1, check_stop)
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
            self.smart_sleep(2, check_stop)
            self.mouse.click(950,900)  # 点击确认购买后关闭提示框
            self.smart_sleep(1, check_stop)
            self.mouse.click(1830,60) # 点击关闭购买界面
            self.smart_sleep(2, check_stop)
            msg_buy_success = f"已成功购买鱼饵，继续执行钓鱼任务..."
            if logger: logger(msg_buy_success)
            else: print(msg_buy_success)
            self.keyboard.press_key('e') # 按下 'E' 键装备鱼饵
            self.smart_sleep(1, check_stop)
            self.mouse.click(1170,700) # 点击更换鱼饵
            self.smart_sleep(1, check_stop)

    def sell_fish(self, logger=None, check_stop=None):
        self.keyboard.press_key('q')  # 模拟按下 'Q' 键打开商店界面
        self.smart_sleep(1, check_stop)
        self.mouse.click(150, 400)  # 点击到鱼饵分类
        self.smart_sleep(1, check_stop)
        save_parh_shop = self.execute_screenshot(logger=logger)  # 再次截图，检测商店界面是否正确打开
        roi_shop = [550,500,850,750] 
        similarity_if_fish = self.matcher.compare_similarity(screen_image=save_parh_shop, reference_image="fish-10.png", roi=roi_shop)
        self.smart_sleep(1, check_stop)
        if similarity_if_fish < 0.8:
            self.mouse.click(1060, 960)  # 点击卖出
            self.smart_sleep(1, check_stop)
            self.mouse.click(1170, 700)  # 点击确认卖出
            self.smart_sleep(1, check_stop)
            self.mouse.click(1830,60) # 点击关闭商店界面
            self.smart_sleep(1, check_stop)
        else:
            msg_shop = f"商店界面没有鱼可以卖出"
            if logger: logger(msg_shop)
            else: print(msg_shop)
        self.mouse.click(1830,60) # 点击关闭商店界面
        self.smart_sleep(1, check_stop)

    def _run_once_impl(self, logger, cnt, root_dir, check_stop):
        if cnt == 1:
            # 这里可以添加对初始钓鱼界面的识别校验
            # similarity = self.matcher.compare_similarity(saved_path, r"assets\images\fishing-start.png")
            pass
        msg_start = f"第 {cnt} 次执行钓鱼任务..."
        if logger: logger(msg_start)
        else: print(msg_start)
        if self.begin_fishing(logger=logger):
            self.keyboard.press_key('f')  # 模拟按下 'F' 键开始钓鱼
            self.smart_sleep(0.5, check_stop)  # 等待提示出现
            saved_path = self.execute_screenshot(logger=logger)  # 立即截图，检测是否提示鱼饵用完
            roi_bait = [780,500,1150,580] # 鱼饵用完提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
            similarity_bait = self.matcher.compare_similarity(screen_image=saved_path, reference_image="fish-6.png", roi=roi_bait)
            if similarity_bait > 0.7:
                msg_bait = f"检测到鱼饵用完提示，正在自动购买鱼饵..."
                if logger: logger(msg_bait)
                else: print(msg_bait)
                self.sell_fish(logger=logger, check_stop=check_stop)  # 卖鱼
                self.buy_fish(logger=logger, check_stop=check_stop)  # 买鱼饵
                self.keyboard.press_key('f')  # 再次按下 'F' 键开始钓鱼
            else:
                msg = f"检测到钓鱼按钮，准备执行钓鱼任务！"
                if logger: logger(msg)
                else: print(msg)
                print("未检测到鱼饵用完提示，相似度为{}，继续执行钓鱼任务...".format(similarity_bait))
            self.keyboard.press_key('f')  # 按下 'F' 键开始钓鱼
            bar_roi = [600,60,1325,90] # 钓鱼进度条的 ROI 区域坐标示例 [x1, y1, x2, y2]
            live_screen = self.capturer.grab_screen()
            status = self.matcher.get_fishing_bar_status(live_screen, roi_rect=bar_roi)
            while status is None: 
                self.smart_sleep(0.1, check_stop) # 等待 100ms 
                self.keyboard.press_key('f')  # 再次按下 'F' 键开始钓鱼
                live_screen = self.capturer.grab_screen()
                status = self.matcher.get_fishing_bar_status(live_screen, roi_rect=bar_roi)
        else:
            msg = f"未检测到钓鱼按钮，无法执行钓鱼任务！请检查游戏画面是否正确，或调整模板图片和阈值。"
            raise RuntimeError(msg)
        
        """
        开始执行钓鱼溜鱼小游戏的核心逻辑
        """
        if logger: logger(">>> 鱼咬钩了！进入溜鱼模式...")
        else: print(">>> 鱼咬钩了！进入溜鱼模式...")
        self.slip_records = []
        while True:
            if check_stop: check_stop()  # 【新增】：溜鱼期间时刻检查信号！
            # 1. 瞬间截取内存画面 (极速)
            live_screen = self.capturer.grab_screen()
            self.slip_records.append((f"fish_{cnt}_{int(time.time()*1000)}.png", live_screen))
            # 2. 获取当前进度条状态
            status = self.matcher.get_fishing_bar_status(live_screen, roi_rect=bar_roi)
            if status is None: #加强一次
                self.smart_sleep(0.1, check_stop) # 等待 100ms 再试一次，避免偶尔的截图失败导致误判
                live_screen = self.capturer.grab_screen()
                self.slip_records.append((f"fish_{cnt}_{int(time.time()*1000)}.png", live_screen))
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
            # 计算绿条的中心点
            safe_center = (safe_left + safe_right) // 2
            if current_pos < safe_center - 10:
                if logger: pass
                else: print(f"偏左 ({current_pos})，正在向右拉...")
                self.keyboard.press_key('d')
            elif current_pos > safe_center + 10:
                if logger: pass
                else: print(f"偏右 ({current_pos})，正在向左拉...")
                self.keyboard.press_key('a')
            else:pass 
        
        save_parh = self.execute_screenshot(logger=logger)  # 最后再截图一次，记录结果
        roi_seccess = [840,960,1080,1000] # 钓鱼成功提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
        roi_fail = [850,500,1050,580] # 钓鱼失败提示的 ROI 区域坐标示例 [x1, y1, x2, y2]
        similarity_success = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-4.png", roi=roi_seccess)
        similarity_fail = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-5.png", roi=roi_fail)
        pre_time = time.time()
        while True:
            if check_stop: check_stop()  # 【新增】：等待结算画面时时刻检查信号！
            if time.time() - pre_time > 15:  # 超过 15 秒还未检测到结果，认为异常
                meg=f"长时间未检测到钓鱼结果，任务执行异常！"
                raise RuntimeError(meg)
            if similarity_success > 0.8:
                if logger: logger("钓鱼成功！")
                else: print("钓鱼成功！")
                break
            elif similarity_fail > 0.8:
                if logger: logger("钓鱼失败了！")
                else: print("钓鱼失败了！")
                
                # 在复制到 error 文件夹之前，必须先将内存中的截图落盘，否则复制过去的是空文件夹
                if hasattr(self, 'slip_records') and self.slip_records:
                    import concurrent.futures
                    def _save_fail_img(item):
                        fname, f = item
                        if f is not None and getattr(f, 'size', 0) > 0:
                            cv2.imencode('.png', f)[1].tofile(os.path.join(self.current_temp_dir, fname))
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        executor.map(_save_fail_img, self.slip_records)
                    self.slip_records.clear()

                timestamp = time.strftime("%Y%m%d_%H%M%S")
                error_dir = os.path.join(root_dir, "error")
                os.makedirs(error_dir, exist_ok=True)
                error_folder_path = os.path.join(error_dir, f"fish_{cnt}_{timestamp}_钓鱼失败")
                
                import shutil
                if os.path.exists(self.current_temp_dir):
                    shutil.copytree(self.current_temp_dir, error_folder_path)
                    
                if logger: logger(f"已保存失败截图文件夹以供分析: {error_folder_path}")
                else: print(f"已保存失败截图文件夹以供分析: {error_folder_path}")

                break
            else:
                # 如果两者都没有检测到，说明可能提示还没出来，继续等待
                self.smart_sleep(0.01, check_stop)
                save_parh = self.execute_screenshot(logger=logger)
                similarity_success = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-4.png", roi=roi_seccess)
                similarity_fail = self.matcher.compare_similarity(screen_image=save_parh, reference_image="fish-5.png", roi=roi_fail)

        while True:
            self.mouse.click(960, 540)  # 点击屏幕中央，关闭结果提示框
            self.smart_sleep(0.5, check_stop)
            live_screen = self.capturer.grab_screen()  # 确认结果提示框已经关闭了
            similarity_success = self.matcher.compare_similarity(screen_image=live_screen, reference_image="fish-4.png", roi=roi_seccess)
            if similarity_success < 0.8:break
        
        if logger: logger("正在将溜鱼期间的截图保存到本地...")
        else: print("正在将溜鱼期间的截图保存到本地(多线程提速)...")
        import concurrent.futures
        def _save_normal_img(item):
            fname, f = item
            if f is not None and getattr(f, 'size', 0) > 0:
                cv2.imencode('.png', f)[1].tofile(os.path.join(self.current_temp_dir, fname))
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(_save_normal_img, self.slip_records)
        self.slip_records.clear()

        # 结束确认处理，比如关闭结算页面等...
        msg_end = f"第 {cnt} 次钓鱼任务执行完毕。"
        if logger: logger(msg_end)
        else: print(msg_end)


    def execute_screenshot(self, logger=None):
        """
        调用 ScreenCapturer 截图并保存。
        如果截图失败，抛出 RuntimeError 异常。
        """
        save_dir = getattr(self, 'current_temp_dir', 'temp')
        # 直接调用原有的截图方法，不传入 prefix 参数以防报错
        saved_path = self.capturer.save_screenshot(save_dir, logger=logger)
        
        # 截图完成后，在外部将其重命名为我们需要的规范命名 (fish_cnt+时间)
        if saved_path and os.path.exists(saved_path):
            cnt = getattr(self, 'current_cnt', 0)
            # 使用带毫秒的时间戳，防止一秒内多张图互相覆盖
            new_filename = f"fish_{cnt}_{int(time.time()*1000)}.png"
            new_saved_path = os.path.join(save_dir, new_filename)
            try:
                os.rename(saved_path, new_saved_path)
                saved_path = new_saved_path
            except Exception as e:
                if logger: logger(f"截图重命名失败: {e}")
                
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
    input("按回车键退出...")