import sys
import os
import time

# 将项目根目录加进系统路径，方便单独运行这个文件进行测试
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.vision.screen import ScreenCapturer
from src.control.mouse_kbd import MouseController
from src.vision.matcher import ImageMatcher
from src.vision.number import NumberReader

# 全局常量：麻将任务相关的固定按键坐标
BTN_POS = {
    "START_MATCH": (1650, 980),        # 准备按钮
    "EXIT": (50, 50),                  # 左上角退出/结算返回按钮
    "SELECT_ROLE": (1350,1010),        # 选择角色按钮
    "ROLE_1": (160, 300),              # 角色1
    "ROLE_2": (340, 300),              # 角色2
    "ROLE_3": (520, 300),              # 角色3
    "CONFIRM": (960,750),              # 确认按钮
    "WAN": (810,730),                  # 万
    "TONG": (950,730),                 # 筒
    "TIAO": (1100,730),                # 条
    "HU":(85,470),                     # 胡
    "PENG":(85,570),                   # 碰
    "CHU":(85,670),                    # 出
}

class MajiangTask:
    def __init__(self, window_title="异环"):
        """初始化麻将任务对象"""
        self.capturer = ScreenCapturer(window_title)
        self.mouse = MouseController(window_title)
        self.matcher = ImageMatcher()
        self.readnum = NumberReader()

    def run_once(self,logger=None,cnt=0):
        """
        执行一遍单次的麻将任务核心逻辑。
        """
        # 第一步：获取当前游戏截图 (测试画面获取)
        saved_path = self.execute_screenshot(logger=logger)
        if cnt==1:
            similarity = self.matcher.compare_similarity(saved_path, r"assets\images\majian-1.png")
            match_msg = f"当前画面与默认图片的匹配度为: {similarity:.2f}"
            if logger:
                logger(match_msg)  # 如果有 UI 界面，输出到 UI 日志框
            else:
                print(match_msg)   # 如果是单独运行此文件测试，直接打印在控制台
            
            if(similarity < 0.8):
                error_msg = "当前画面与预设模板匹配度过低，可能未正确识别游戏界面或游戏状态异常。"
                if logger:
                    logger(error_msg)
                else:
                    print(error_msg)
                raise RuntimeError("画面识别失败，无法继续执行麻将任务。")
            #选择角色
            self.mouse.click(*BTN_POS["SELECT_ROLE"])
            time.sleep(1)
            self.mouse.click(*BTN_POS["ROLE_1"])
            time.sleep(1)
            self.mouse.click(*BTN_POS["ROLE_2"])
            time.sleep(1)
            self.mouse.click(*BTN_POS["ROLE_3"])
            time.sleep(1)
        
        if logger:
            logger(f"第 {cnt} 次执行麻将任务，已成功获取游戏画面。")
        else:
            print(f"第 {cnt} 次执行麻将任务，已成功获取游戏画面。")
        

        #点击准备和确认
        self.mouse.click(*BTN_POS["START_MATCH"])
        time.sleep(3)
        self.mouse.click(*BTN_POS["CONFIRM"])
        time.sleep(3) # 等待匹配和动画完成

        #找牌区域亮起的牌，模拟点击（测试图像匹配和自动点击）
        cards_roi = [700, 650, 1200, 800] 
        saved_path = self.execute_screenshot(logger=logger) # 再次截图，获取最新的游戏画面
        # 调用新方法寻找亮起的牌
        highlighted_card_pos = self.matcher.find_white_border_target(saved_path, roi_rect=cards_roi)

        if highlighted_card_pos:
            pai="未知牌"
            if 750 <= highlighted_card_pos[0] <= 850:
                pai = "万"
            if 900 <= highlighted_card_pos[0] <= 1000:
                pai = "筒"
            if 1050 <= highlighted_card_pos[0] <= 1150:
                pai = "条"
            if pai=="未知牌":
                if logger:
                    logger(f"异常：发现亮起的牌，但无法确定类型，坐标: {highlighted_card_pos}，准备点击...")
                else:
                    print(f"异常：发现亮起的牌，但无法确定类型，坐标: {highlighted_card_pos}，准备点击...")
            else:
                if logger:
                    logger(f"发现亮起的牌 {pai}！坐标: {highlighted_card_pos}，准备点击...")
                else:
                    print(f"发现亮起的牌 {pai}！坐标: {highlighted_card_pos}，准备点击...")
                
            # 直接让鼠标点击找到的坐标
            self.mouse.click(highlighted_card_pos[0], highlighted_card_pos[1])
        else:
            msg = "异常：当前没有亮起的牌。"
            if logger: logger(msg)
            else: print(msg)
        
        #点击自动打牌的按钮（这里先模拟点击胡碰出，后续可以根据实际牌面和策略动态选择）
        time.sleep(1)
        self.mouse.click(*BTN_POS["HU"])
        time.sleep(1)
        self.mouse.click(*BTN_POS["PENG"])
        time.sleep(1)
        self.mouse.click(*BTN_POS["CHU"])
        time.sleep(1)
        pre=55 
        while True:
            saved_path = self.execute_screenshot(logger=logger) # 再次截图，获取最新的游戏画面
            number = self.readnum.read_remaining_tiles(saved_path)
            while pre-number >= 5:
                saved_path = self.execute_screenshot(logger=logger) # 再次截图，获取最新的游戏画面
                number = self.readnum.read_remaining_tiles(saved_path)
            if number != -1:
                msg = f"当前剩余牌数: {number} 张"
            else:
                msg = "异常：未识别到剩余牌数"
            if logger:
                logger(msg)
            else:
                print(msg)
            time.sleep(5) # 每 5 秒更新一次剩余牌数
            if number <= 0:
                break
            pre=number
        while True:
            saved_path = self.execute_screenshot(logger=logger) # 再次截图，获取最新的游戏画面
            my_roi = [900, 850, 1800, 950]
            similarity = self.matcher.compare_similarity(saved_path, r"assets\images\majian-5.png", roi=my_roi)
            if similarity > 0.8:
                self.mouse.click(1550,900) # 再来一次
                break
            else:
                time.sleep(1)
        

    def execute_screenshot(self,logger=None):
        """
        调用 ScreenCapturer 截图并保存。
        如果截图失败，抛出 RuntimeError 异常。
        """
        # 调用我们刚才写好的 save_screenshot 功能
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

    task = MajiangTask("异环")
    try:
        task.run_once()
    except Exception as e:
        print(f"捕获到异常: {e}")