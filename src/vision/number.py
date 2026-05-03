import cv2
import numpy as np
import ddddocr

class NumberReader:
    def __init__(self):
        self.ocr = ddddocr.DdddOcr(show_ad=False) 

    def read_remaining_tiles(self, screen_image):
        if isinstance(screen_image, str):
            img = cv2.imdecode(np.fromfile(screen_image, dtype=np.uint8), cv2.IMREAD_COLOR)
        else:
            img = screen_image

        # 1. 划定 ROI (请根据实际情况修改坐标)
        roi_y1, roi_y2 = 545, 570
        roi_x1, roi_x2 = 900, 1000
        roi = img[roi_y1:roi_y2, roi_x1:roi_x2]

        # 2. 转换成灰度图 (丢弃所有色彩信息，只保留明暗亮度)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        # 3. 核心魔法：使用大津法自动二值化
        # cv2.THRESH_BINARY 表示超过阈值的变白(255)，低于阈值的变黑(0)
        # cv2.THRESH_OTSU 就是告诉 OpenCV：别让我猜阈值了，你自己算！
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # 此时，明亮的数字变成了纯白(255)，暗背景变成了纯黑(0)
        
        # 4. 黑白反转 (OCR 引擎通常更擅长识别 白底黑字)
        binary_inv = cv2.bitwise_not(binary)

        # ====== 调试建议 ======
        # 如果你不确定它切得准不准，把这句话取消注释，运行一次去 temp 文件夹看一眼
        # cv2.imwrite("temp/debug_otsu.png", binary_inv)
        # ======================

        # 5. 格式转换并进行 OCR 识别
        _, img_encoded = cv2.imencode('.png', binary_inv)
        result_str = self.ocr.classification(img_encoded.tobytes())
        
        # 6. 数据清洗 (只保留数字)
        clean_number_str = "".join(filter(str.isdigit, result_str))
        
        if clean_number_str:
            return int(clean_number_str)
        else:
            return -1  # 返回 -1 表示识别失败或没有数字

if __name__ == "__main__":
    # 需要从你之前的模块里导入截图工具
    import sys
    import os
    import ctypes
    
    # 自动获取管理员权限的魔法代码
    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("当前无管理员权限，正在请求 UAC 提权...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        sys.exit()

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from src.vision.screen import ScreenCapturer
    
    # 1. 初始化工具
    capturer = ScreenCapturer("异环 ") # 填入你的游戏窗口名字
    reader = NumberReader()
    
    print("开始获取屏幕截图...")
    # 2. 获取实时画面
    saved_path = capturer.save_screenshot("temp")
    
    if saved_path:
        print(f"截图成功，保存在: {saved_path}")
        # 3. 传给 OCR 进行识别
        number = reader.read_remaining_tiles(saved_path)
        print(f"==== 实时识别到的剩余牌数: {number} ====")
    else:
        print("截图失败，请检查游戏窗口是否被遮挡或最小化。")