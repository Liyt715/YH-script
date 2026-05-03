import cv2
import numpy as np
import os
import sys

# 将项目根目录加进系统路径，方便单独运行这个文件进行测试
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ImageMatcher:
    def __init__(self, templates_dir="assets\\images"):
        """
        初始化图像匹配器
        :param templates_dir: 存放模板图片(你要找的目标小图)的默认根目录
        """
        # 如果你从 src/vision 层面运行，需计算一下绝对路径指向根目录的 assets
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.templates_dir = os.path.join(base_path, templates_dir)

    def _load_image(self, image_source):
        """
        内部辅助方法：加载图片。
        支持传入文件路径字符串，或者直接传入 numpy 数组 (从 screen.py 里直接截的图)。
        """
        if isinstance(image_source, str):
            if not os.path.exists(image_source):
                raise FileNotFoundError(f"找不到图片文件: {image_source}")
            # 使用 imdecode 而不是 imread，这样在 Windows 平台下可以完美支持含有中文的路径
            return cv2.imdecode(np.fromfile(image_source, dtype=np.uint8), cv2.IMREAD_COLOR)
        elif isinstance(image_source, np.ndarray):
            return image_source
        else:
            raise ValueError("不支持的图片来源格式，必须是图片路径或 numpy 数组")

    def find_template(self, screen_image, template_name, threshold=0.8):
        """
        在屏幕截图中寻找指定的模板图片（寻找单个目标）
        
        :param screen_image: 屏幕截图 (可以是保存路径，比如 "temp/scr.png"，也可以是 cv2 内存数组)
        :param template_name: 模板图片的名称或相对路径，比如 "btn_start.png"
        :param threshold: 置信度阈值 (0~1)，默认 0.8。越接近 1 匹配越严格，越不容易误判。
        :return: (center_x, center_y) 元组，如果找不到则返回 None
        """
        # 1. 加载大图（整张屏幕）
        img_screen = self._load_image(screen_image)
        
        # 2. 组装小图（模板）路径并加载
        template_path = template_name
        if not os.path.isabs(template_path) and not os.path.exists(template_path):
            template_path = os.path.join(self.templates_dir, template_name)
        
        if not os.path.exists(template_path):
            print(f"[图像匹配] 找不到小图模板文件: {template_path}")
            return None
            
        img_template = self._load_image(template_path)
        
        # 3. 灰度化。大多数UI匹配不需要颜色信息，转成灰度图能让匹配速度翻倍且更抗干扰
        gray_screen = cv2.cvtColor(img_screen, cv2.COLOR_BGR2GRAY)
        gray_template = cv2.cvtColor(img_template, cv2.COLOR_BGR2GRAY)
        
        # 获取目标小图的高宽
        h, w = gray_template.shape
        
        # 4. 调用 OpenCV 最核心的神级防封匹配算法 (NCC算法)
        res = cv2.matchTemplate(gray_screen, gray_template, cv2.TM_CCOEFF_NORMED)
        
        # 5. 提取最高相似度的位置和数值
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        
        # 6. 如果相似度达标，则计算中心坐标并返回
        if max_val >= threshold:
            top_left_x, top_left_y = max_loc
            # 用左上角坐标加上自身宽高的一半，就是完美的中心点（给鼠标点击用）
            center_x = top_left_x + w // 2
            center_y = top_left_y + h // 2
            
            print(f"[图像匹配] 找到 '{os.path.basename(template_name)}'，相似度: {max_val:.2f}，点击中心为: ({center_x}, {center_y})")
            return (center_x, center_y)
        
        return None

    def find_all_templates(self, screen_image, template_name, threshold=0.8):
        """
        在大图中寻找所有符合的模板（如：麻将桌上有多张一样的牌，你想全找出来）
        :return: [(x1,y1), (x2,y2), ...] 列表
        """
        img_screen = self._load_image(screen_image)
        template_path = template_name if os.path.exists(template_name) else os.path.join(self.templates_dir, template_name)
        
        if not os.path.exists(template_path):
            return []
            
        img_template = self._load_image(template_path)
        gray_screen = cv2.cvtColor(img_screen, cv2.COLOR_BGR2GRAY)
        gray_template = cv2.cvtColor(img_template, cv2.COLOR_BGR2GRAY)
        h, w = gray_template.shape
        
        res = cv2.matchTemplate(gray_screen, gray_template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= threshold)
        
        points = []
        # 一次匹配可能会在一个目标周围产生多个相近的有效点，我们要过滤/去重
        for pt in zip(*loc[::-1]):  # zip(*loc[::-1]) 能将坐标整理成 (x, y) 的形式
            center_x = int(pt[0] + w / 2)
            center_y = int(pt[1] + h / 2)
            
            # 去重：如果这个点附近 10 个像素里已经记录过坐标了，就视为同一个目标，跳过
            is_dup = any(abs(center_x - px) < 10 and abs(center_y - py) < 10 for px, py in points)
            if not is_dup:
                points.append((center_x, center_y))
                
        if points:
            print(f"[图像匹配] 共扫出 {len(points)} 个 '{os.path.basename(template_name)}' 的目标")
        return points

    def compare_similarity(self, screen_image, reference_image,roi=None):
        """
        比较当前图片（如截图）和给定路径的图片（如某个基准图/模板图），并返回它们的最高准确度（相似度）。
        如果你只需要知道“当前屏幕上有没有这个东西”，用这个方法直接获取相似度就行。
        
        :param screen_image: 当前截图 (路径字符串 或 numpy 数组)
        :param reference_image: 作为比较基准的参考图 (路径字符串，如果在 assets/ui 里能自动补全路径)
        :param roi: 【新增】可选参数，特定区域的坐标范围 [x1, y1, x2, y2]。如果提供，只对比该区域。
        :return: float 分数 (0.0 到 1.0 之间)，代表最高相似度/准确度
        """
        # 1. 加载大图
        img_screen = self._load_image(screen_image)
        
        # 2. 加载基准参考图
        ref_path = reference_image
        if isinstance(ref_path, str) and not os.path.isabs(ref_path) and not os.path.exists(ref_path):
            ref_path = os.path.join(self.templates_dir, reference_image)
            
        try:
            img_ref = self._load_image(ref_path)
        except Exception as e:
            print(f"[图像比较] 加载参考图失败: {e}")
            return 0.0

        # ==================== 【新增核心逻辑：处理特定区域 ROI】 ====================
        if roi is not None:
            x1, y1, x2, y2 = roi
            h_s, w_s = img_screen.shape[:2]
            
            # 越界安全校验：防止传入的坐标超出屏幕边界导致程序崩溃
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w_s, x2), min(h_s, y2)
            
            if x1 >= x2 or y1 >= y2:
                print(f"[图像比较] 坐标无效: {roi}")
                return 0.0
                
            # 极速裁剪：用 numpy 切片只保留区域内的画面
            img_screen = img_screen[y1:y2, x1:x2]
            
            # 智能处理参考图：如果你的参考图比这个区域还大（说明它可能也是一张全屏截图）
            # 那就自动把参考图也按照这个区域裁剪一下
            h_r, w_r = img_ref.shape[:2]
            if h_r > (y2 - y1) or w_r > (x2 - x1):
                img_ref = img_ref[y1:y2, x1:x2]
        # ============================================================================
            
        # 3. 转灰度图 (注意：这里转换的已经是裁剪后的小图了，速度会比以前快几十倍)
        gray_screen = cv2.cvtColor(img_screen, cv2.COLOR_BGR2GRAY)
        gray_ref = cv2.cvtColor(img_ref, cv2.COLOR_BGR2GRAY)
        
        # 安全校验：OpenCV 匹配时，模板图绝对不能比大图还大
        h_s, w_s = gray_screen.shape
        h_r, w_r = gray_ref.shape
        if h_r > h_s or w_r > w_s:
            print(f"[图像比较] 参考图({w_r}x{h_r})比截图区域({w_s}x{h_s})还大，无法计算包含相似度")
            return 0.0
            
        # 4. 执行匹配并获取最大相似度
        res = cv2.matchTemplate(gray_screen, gray_ref, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        return float(max_val)

    def find_white_border_target(self, screen_image, roi_rect=None, area_threshold=1000):
        """
        寻找画面中带有白色边框的目标（如高亮的麻将牌），并返回其中心坐标。
        利用 HSV 颜色过滤和轮廓检测实现，相比单纯的模板匹配，这种方法对“点亮”状态的识别极度稳定。

        :param screen_image: 屏幕截图 (可以是保存路径或 numpy 数组)
        :param roi_rect: 感兴趣区域 (Region of Interest)，格式为 [x1, y1, x2, y2]。
                         如果提供，将只在这个区域内搜索，大幅提升速度并避免其他白色 UI 干扰。
                         如果不提供，则在全屏搜索。
        :param area_threshold: 面积阈值，用于过滤掉画面中太小的白色噪点或文字（需根据白边粗细微调）。
        :return: (center_x, center_y) 元组，如果找不到则返回 None
        """
        # 1. 加载图片
        img = self._load_image(screen_image)
        if img is None:
            return None

        # 2. 处理 ROI (截取感兴趣区域)
        if roi_rect:
            x1, y1, x2, y2 = roi_rect
            # 确保坐标在图像范围内
            h, w = img.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            roi = img[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            roi = img
            offset_x, offset_y = 0, 0

        # 3. 转换到 HSV 色彩空间
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 4. 定义白色的 HSV 范围
        # H (色相) 0-180 都可以
        # S (饱和度) 要极低，0-30
        # V (亮度) 要极高，200-255 (可以根据游戏画面的实际亮度稍微调低这个下限，比如 180)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])

        # 5. 提取白色遮罩 (白边变成纯白，其他变黑)
        mask = cv2.inRange(hsv, lower_white, upper_white)

        # 6. 寻找轮廓
        # cv2.findContours 在不同版本的 OpenCV 返回值数量可能不同，但倒数第一个总是 hierarchy，倒数第二个是 contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 7. 遍历所有找到的轮廓
        for c in contours:
            area = cv2.contourArea(c)
            # 过滤掉面积太小的干扰项
            if area > area_threshold:
                # 8. 计算轮廓的几何中心 (图像矩)
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])

                    # 9. 还原为基于全屏的绝对坐标
                    final_x = cx + offset_x
                    final_y = cy + offset_y

                    print(f"[特征识别] 找到符合条件的白色边框目标，中心点为: ({final_x}, {final_y})")
                    return (final_x, final_y)

        # 如果遍历完都没找到面积达标的白色边框
        return None
    
    def find_transparent_ui(self, screen_image, template_name, roi_rect=None, threshold=0.8):
        """
        专门用于寻找带有透明背景/动态背景的高亮纯色UI按钮
        :param screen_image: 当前屏幕截图 (路径字符串 或 numpy 数组)
        :param template_name: 纯色UI模板图的文件名或路径（必须是纯白色图标，且背景透明或动态）
        :param roi_rect: 可选的感兴趣区域坐标 [x1, y1, x2, y2]，如果提供，将只在这个区域内搜索
        :param threshold: 匹配阈值，默认 0.8
        """
        img_screen = self._load_image(screen_image)
        
        # 处理小图路径
        template_path = template_name if os.path.exists(template_name) else os.path.join(self.templates_dir, template_name)
        img_template = self._load_image(template_path)
        
        # 1. 如果有 ROI，先裁剪屏幕（极大提高速度）
        if roi_rect:
            x1, y1, x2, y2 = roi_rect
            img_screen = img_screen[y1:y2, x1:x2]
            offset_x, offset_y = x1, y1
        else:
            offset_x, offset_y = 0, 0
            
        # 2. 转为灰度图
        gray_screen = cv2.cvtColor(img_screen, cv2.COLOR_BGR2GRAY)
        gray_template = cv2.cvtColor(img_template, cv2.COLOR_BGR2GRAY)
        
        # 3. 核心：固定阈值二值化（过滤掉背景）
        # 提取亮度大于 200 的像素（纯白图标），其他全变黑。
        # 注意：这个 200 可能需要根据游戏实际亮度微调 (200~255 之间)
        _, binary_screen = cv2.threshold(gray_screen, 200, 255, cv2.THRESH_BINARY)
        _, binary_template = cv2.threshold(gray_template, 200, 255, cv2.THRESH_BINARY)
        
        # 4. 在两张黑白图上进行模板匹配
        res = cv2.matchTemplate(binary_screen, binary_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        
        if max_val >= threshold:
            h, w = binary_template.shape
            center_x = max_loc[0] + w // 2 + offset_x
            center_y = max_loc[1] + h // 2 + offset_y
            print(f"[UI识别] 找到目标，匹配度: {max_val:.2f}，坐标: ({center_x}, {center_y})")
            return (center_x, center_y, w, h)
        else:
            print(f"[UI识别] 未找到目标，最高匹配度: {max_val:.2f}")
            pass
        return None
    def get_fishing_bar_status(self, screen_image, roi_rect):
        """
        识别钓鱼进度条中“绿色安全区”的范围和“黄色指示线”的位置。
        
        :param screen_image: 屏幕截图 (路径或 numpy 数组)
        :param roi_rect: 必须提供！钓鱼条所在的粗略区域 [x1, y1, x2, y2]，用于排除画面其他部分的颜色干扰
        :return: 字典包含状态信息，例如 {'green_left': 100, 'green_right': 300, 'yellow_x': 150}
                 如果识别失败则返回 None
        """
        img = self._load_image(screen_image)
        if img is None:
            return None

        # 1. 严格裁剪 ROI (极大地排除背景中樱花、建筑的干扰，同时大幅提升速度)
        x1, y1, x2, y2 = roi_rect
        roi = img[y1:y2, x1:x2]
        offset_x = x1 # 用于最后将坐标还原到全屏坐标系

        # 2. 转换到 HSV 色彩空间
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # ==========================================
        # 3. 提取绿色安全区范围
        # ==========================================
        # 设定青绿色的 HSV 范围 (OpenCV中 H的范围是 0-179)
        # 如果颜色偏蓝，把 H 的上限调高；如果偏纯绿，把 H 的下限调低
        lower_green = np.array([60, 100, 100])
        upper_green = np.array([95, 255, 255])
        
        mask_green = cv2.inRange(hsv, lower_green, upper_green)
        
        # 寻找绿色区域的轮廓
        contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        green_left = -1
        green_right = -1
        
        if contours_green:
            # 找到面积最大的绿色轮廓 (防止细小噪点干扰)
            largest_green = max(contours_green, key=cv2.contourArea)
            if cv2.contourArea(largest_green) > 50: # 面积太小说明是噪点
                # 获取该轮廓的边界框
                xg, yg, wg, hg = cv2.boundingRect(largest_green)
                # 还原为全屏 X 坐标
                green_left = xg + offset_x
                green_right = xg + wg + offset_x

        # ==========================================
        # 4. 提取黄色指示线位置
        # ==========================================
        # 设定黄色的 HSV 范围
        lower_yellow = np.array([20, 100, 150])
        upper_yellow = np.array([35, 255, 255])
        
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        
        contours_yellow, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        yellow_x = -1
        
        if contours_yellow:
            largest_yellow = max(contours_yellow, key=cv2.contourArea)
            if cv2.contourArea(largest_yellow) > 10: # 黄线比较细，面积阈值设小一点
                xy, yy, wy, hy = cv2.boundingRect(largest_yellow)
                # 黄线的中心X坐标
                yellow_x = xy + (wy // 2) + offset_x

        # ==========================================
        # 5. 结果校验与返回
        # ==========================================
        if green_left != -1 and yellow_x != -1:
            return {
                "green_left": green_left,
                "green_right": green_right,
                "yellow_x": yellow_x,
                # 你甚至可以直接在这里算出黄线是不是在安全区内
                "is_safe": green_left <= yellow_x <= green_right
            }
        
        return None
# ==================== 可视化测试代码 ====================
if __name__ == "__main__":
    import sys
    import os
    import cv2
    import ctypes
    import time
    
    # 确保导入了你需要用到的自定义类
    from src.vision.screen import ScreenCapturer
    from src.vision.matcher import ImageMatcher 

    if not ctypes.windll.shell32.IsUserAnAdmin():
        print("当前无管理员权限，正在请求 UAC 提权...")
        # 使用 python.exe 启动，保留控制台黑框以便查看输出
        exe = sys.executable
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, __file__, None, 1)
        time.sleep(2)
        sys.exit()
    
    # 1. 实例化你的类
    matcher = ImageMatcher() 
    
    # 【修复点】：不要用 self 做全局变量名，改用 capturer
    capturer = ScreenCapturer(window_title="异环") 
    
    # 1. 动态获取项目根目录
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    
    # 【修复点】：调用 capturer 的方法
    test_screen_path = capturer.save_screenshot(save_dir="temp") 
    
    test_roi=[600,60,1325,90] # 你要测试的 ROI 区域坐标 [x1, y1, x2, y2]
    