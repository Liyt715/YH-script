import sys
import time
import os
import shutil
import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                               QWidget, QTextEdit, QLabel, QHBoxLayout, QListWidget, 
                               QStackedWidget, QGroupBox, QCheckBox, QSpinBox)
from PySide6.QtCore import Qt, QThread, Signal

from src.tasks.majiang_task import MajiangTask
from src.tasks.fishing_task import FishingTask
from src.control.mouse_kbd import MouseController

class MajiangThread(QThread):
    log_signal = Signal(str)

    def __init__(self, infinite_loop=True, max_times=1):
        super().__init__()
        self.is_running = True
        self.infinite_loop = infinite_loop
        self.max_times = max_times
        self.mouse = MouseController("异环")

    def run(self):
        """麻将任务后台线程"""
        if self.infinite_loop:
            self.log_signal.emit(">>> [自动麻将] 工作线程已启动 (模式: 无限循环)")
        else:
            self.log_signal.emit(f">>> [自动麻将] 工作线程已启动 (模式: 计划执行 {self.max_times} 次)")
            
        try:
            # 初始化我们之前写好的麻将任务类
            task = MajiangTask("异环")
        except Exception as e:
            self.log_signal.emit(f"初始化失败: {e}")
            return

        current_count = 0
        while self.is_running:
            # 如果不是无限循环，并且当前次数已经达到了设定的最大次数，就跳出循环！
            if not self.infinite_loop and current_count >= self.max_times:
                self.log_signal.emit(f">>> [自动麻将] 设定的 {self.max_times} 次任务已全部完成！")
                break

            try:
                current_count += 1
                # 模拟处理时间（等待动画或下一回合发牌），实际开发时可根据逻辑动态 time.sleep
                time.sleep(2)
                # 调用一次完整的打牌动作（这个方法写在 majiang_task.py 里）
                task.run_once(logger=self.log_signal.emit,cnt=current_count)  # 传入日志函数，让它能直接输出到 UI 界面
                self.log_signal.emit(f"[第 {current_count} 次] 麻将动作执行成功")
                if not self.infinite_loop and current_count >= self.max_times:
                    time.sleep(2) # 等待最后一次动作的动画结束
                    self.mouse.click(50,50) # 点击左上角退出按钮
                    time.sleep(1)
                    self.mouse.click(1150,700) # 点击确认退出按钮
                    break
            except RuntimeError as e:
                # 【修改点】专门捕获底层主动扔出来的业务炸弹（截图失败、找不到窗口、识别超时）
                self.log_signal.emit(f'<span style="color: red;"><b>【任务中断】 {str(e)}</b></span>')
                self.is_running = False # 停止循环
                
            except Exception as e:
                # 【修改点】捕获代码本身的 Bug（比如越界、空指针异常等）
                self.log_signal.emit(f'<span style="color: red;"><b>【严重崩溃】 未知代码异常: {str(e)}</b></span>')
                self.is_running = False # 停止循环
        
        self.log_signal.emit(">>> [自动麻将] 工作线程已安全结束")

    def stop(self):
        """通知线程停止并等待完成"""
        self.is_running = False
        self.wait()

class FishingThread(QThread):
    # 定义一个信号，用于将后台文本发送给主界面
    log_signal = Signal(str)

    def __init__(self, infinite_loop=True, max_times=1):
        super().__init__()
        self.is_running = True
        self.infinite_loop = infinite_loop
        self.max_times = max_times
        self.success_count = 0
        self.fail_count = 0

    def run(self):
        """线程启动时执行的代码（后台死循环）"""
        if self.infinite_loop:
            self.log_signal.emit(">>> [自动钓鱼] 工作线程已启动 (模式: 无限循环)")
        else:
            self.log_signal.emit(f">>> [自动钓鱼] 工作线程已启动 (模式: 计划执行 {self.max_times} 次)")
        
        try:
            # 初始化钓鱼任务类
            task = FishingTask("异环")
        except Exception as e:
            self.log_signal.emit(f"初始化钓鱼任务失败: {e}")
            return

        current_count = 0
        
        def task_logger(msg):
            if "钓鱼成功！" in msg:
                self.success_count += 1
            elif "钓鱼失败了！" in msg:
                self.fail_count += 1
            self.log_signal.emit(msg)

        while self.is_running:
            if not self.infinite_loop and current_count >= self.max_times:
                self.log_signal.emit(f">>> [自动钓鱼] 设定的 {self.max_times} 次任务已全部完成！")
                break

            try:
                current_count += 1
                time.sleep(0.5) # 等待0.5秒
                # 调用钓鱼单次任务核心逻辑，并传入 UI 打印槽函数
                task.run_once(logger=task_logger, cnt=current_count)
            except RuntimeError as e:
                self.log_signal.emit(f'<span style="color: red;"><b>【钓鱼中断】 {str(e)}</b></span>')
                self.is_running = False
            except Exception as e:
                self.log_signal.emit(f'<span style="color: red;"><b>【系统异常】 未知代码异常: {str(e)}</b></span>')
                self.is_running = False
        self.log_signal.emit(">>> [自动钓鱼] 后台工作线程已安全结束")
        self.log_signal.emit(f">>> [任务统计] 一共执行钓鱼 {current_count} 次，其中成功 {self.success_count} 次，失败 {self.fail_count} 次。")

    def stop(self):
        """通知线程停止并等待完成"""
        self.is_running = False
        self.wait() # 等待线程安全退出，防止资源泄露导致奔溃


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("异环脚本")
        self.resize(800, 500) # 加宽窗口以容纳三栏布局

        # 核心部件和主布局 (水平布局：左、中、右)
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # ==================== 左侧：任务选择列表 ====================
        self.task_list = QListWidget()
        self.task_list.setFixedWidth(150)
        self.task_list.addItem("自动钓鱼")
        self.task_list.addItem("自动麻将") 
        self.task_list.addItem("test") # 测试用
        main_layout.addWidget(self.task_list)

        # ==================== 中间：任务设置与控制 ====================
        middle_widget = QWidget()
        middle_layout = QVBoxLayout()
        middle_widget.setFixedWidth(400)

        # QStackedWidget 就像一本书，每次只显示一页（用于切换不同任务的设置）
        self.settings_stack = QStackedWidget()

        # 1. 钓鱼任务的设置页面
        fishing_settings = QGroupBox("钓鱼设置")
        f_layout = QVBoxLayout()
        
        # 一直执行（无限循环）的勾选框
        self.cb_infinite_fishing = QCheckBox("一直执行 (无限循环)")
        self.cb_infinite_fishing.setChecked(True) # 默认勾选
        f_layout.addWidget(self.cb_infinite_fishing)
        
        # 指定次数的输入框区域
        f_times_layout = QHBoxLayout()
        f_times_layout.addWidget(QLabel("挂机次数:"))
        self.spin_fishing_times = QSpinBox()
        self.spin_fishing_times.setRange(1, 999) # 最小1次，最大999次
        self.spin_fishing_times.setValue(1)
        self.spin_fishing_times.setEnabled(False) # 因为默认是无限循环，所以先把输入框变灰禁用
        f_times_layout.addWidget(self.spin_fishing_times)
        f_times_layout.addStretch() # 把输入框挤到左边对齐
        f_layout.addLayout(f_times_layout)

        # 信号连结：如果勾选了“一直执行”，次数输入框就禁用；取消勾选，输入框就恢复可用
        self.cb_infinite_fishing.toggled.connect(
            lambda checked: self.spin_fishing_times.setDisabled(checked)
        )

        f_layout.addStretch() # 把组件往上顶
        fishing_settings.setLayout(f_layout)
        self.settings_stack.addWidget(fishing_settings)

        # 2. 麻将任务的设置页面
        mahjong_settings = QGroupBox("麻将设置")
        m_layout = QVBoxLayout()
        
        # 一直执行（无限循环）的勾选框
        self.cb_infinite_mahjong = QCheckBox("一直执行 (无限循环)")
        self.cb_infinite_mahjong.setChecked(True) # 默认勾选
        m_layout.addWidget(self.cb_infinite_mahjong)
        
        # 指定次数的输入框区域
        times_layout = QHBoxLayout()
        times_layout.addWidget(QLabel("挂机次数:"))
        self.spin_mahjong_times = QSpinBox()
        self.spin_mahjong_times.setRange(1, 999) # 最小1次，最大999次
        self.spin_mahjong_times.setValue(1)
        self.spin_mahjong_times.setEnabled(False) # 因为默认是无限循环，所以先把输入框变灰禁用
        times_layout.addWidget(self.spin_mahjong_times)
        times_layout.addStretch() # 把输入框挤到左边对齐
        m_layout.addLayout(times_layout)

        # 信号连结：如果勾选了“一直执行”，次数输入框就禁用；取消勾选，输入框就恢复可用
        self.cb_infinite_mahjong.toggled.connect(
            lambda checked: self.spin_mahjong_times.setDisabled(checked)
        )

        m_layout.addStretch()
        mahjong_settings.setLayout(m_layout)
        self.settings_stack.addWidget(mahjong_settings)

        middle_layout.addWidget(self.settings_stack)

        # 状态提示
        self.status_label = QLabel("当前状态: 待机")
        self.status_label.setAlignment(Qt.AlignCenter)
        middle_layout.addWidget(self.status_label)
        
        # 启动/停止按钮
        self.btn_start = QPushButton("启动任务")
        self.btn_start.clicked.connect(self.on_click_start)
        self.btn_start.setMinimumHeight(40)
        middle_layout.addWidget(self.btn_start)

        middle_widget.setLayout(middle_layout)
        main_layout.addWidget(middle_widget)

        # ==================== 右侧：日志输出 ====================
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("运行日志将在此显示...")
        right_layout.addWidget(self.log_output)
        
        self.btn_clear_log = QPushButton("清除日志")
        self.btn_clear_log.clicked.connect(self.on_click_clear_log)
        right_layout.addWidget(self.btn_clear_log)
        
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # ---------- 信号连接 ----------
        # 左侧列表切换时，自动改变中间 settings_stack 显示的“页码”
        self.task_list.currentRowChanged.connect(self.settings_stack.setCurrentIndex)
        # 默认选中第一项
        self.task_list.setCurrentRow(0)
        
        # 保存线程的变量
        self.task_thread = None

    def log(self, text):
        """带颜色和时间戳的富文本日志"""
        time_str = datetime.datetime.now().strftime("%m-%d %H:%M:%S")
        default_color = "#FFFFFF"
        # 根据关键词自动上色
        if "成功" in text or "完成" in text:
            # 绿色
            html_text = f'<span style="color: green;">[{time_str}] {text}</span>'
        elif "异常" in text or "失败" in text or "报错" in text:
            # 红色加粗
            html_text = f'<span style="color: red;">[{time_str}] <b>{text}</b></span>'
        elif ">>>" in text:
            # 蓝色（系统级提示）
            html_text = f'<span style="color: lightblue;">[{time_str}] {text}</span>'
        else:
            # 普通黑色/灰色
            html_text = f'<span style="color: {default_color};">[{time_str}] {text}</span>'
            
        self.log_output.append(html_text)

    def on_task_finished(self):
        """当线程自然结束（如指定次数达到）时，自动恢复界面状态"""
        if self.btn_start.text() == "停止任务": # 说明此时不是由于用户主动点“停止”按钮造成的退出
            self.btn_start.setText("启动任务")
            self.status_label.setText("当前状态: 待机")
            self.status_label.setStyleSheet("")
            self.task_thread = None
            self.clean_temp_dir() # 任务结束后自动清理临时文件（如果你希望保留截图记录，就注释掉这一行）

    def on_click_start(self):
        if self.btn_start.text() == "启动任务":
            # 根据当前左侧列表选择的任务，分配对应的后台线程
            current_task_idx = self.task_list.currentRow()
            if current_task_idx == 0:
                is_infinite = self.cb_infinite_fishing.isChecked()
                times = self.spin_fishing_times.value()
                self.task_thread = FishingThread(infinite_loop=is_infinite, max_times=times)
            elif current_task_idx == 1:
                # 获取界面上勾选的参数并传给麻将线程
                is_infinite = self.cb_infinite_mahjong.isChecked()
                times = self.spin_mahjong_times.value()
                self.task_thread = MajiangThread(infinite_loop=is_infinite, max_times=times)
            else:
                self.log(">>> 该任务尚未实现具体的后台逻辑！")
                return

            # 1. 改变 UI 状态
            self.btn_start.setText("停止任务")
            self.status_label.setText("当前状态: 运行中...")
            self.status_label.setStyleSheet("color: green;")
            
            # 2. 启动刚才分发的对应线程
            self.task_thread.log_signal.connect(self.log) 
            # 绑定线程自然结束（比如次数跑完了）时的事件，自动恢复按钮状态
            self.task_thread.finished.connect(self.on_task_finished)
            self.task_thread.start() # 开始执行 run() 函数
        else:
            # 1. 恢复 UI 状态
            self.btn_start.setText("启动任务")
            self.status_label.setText("当前状态: 待机")
            self.status_label.setStyleSheet("")
            self.log("正在停止任务，请稍候...")
            
            # 2. 停止线程
            if self.task_thread:
                self.task_thread.stop()
                self.task_thread = None
                
            # 3. 清理临时文件
            self.clean_temp_dir()

    def on_click_clear_log(self):
        """清除日志并保存到logs文件夹"""
        log_text = self.log_output.toPlainText()
        if not log_text.strip():
            return
            
        # 获取外层根目录的 logs 文件夹路径
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logs_dir = os.path.join(root_dir, "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        time_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_name = f"script_log_{time_str}.txt"
        log_file_path = os.path.join(logs_dir, log_file_name)
        
        try:
            with open(log_file_path, "w", encoding="utf-8") as f:
                f.write(log_text)
            self.log_output.clear()
        except Exception as e:
            self.log(f">>> [错误] 保存日志失败: {e}")

    def clean_temp_dir(self):
        """清理临时文件夹中的所有数据"""
        # 获取外层根目录的 temp 文件夹路径
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        temp_dir = os.path.join(root_dir, "temp")
        
        if os.path.exists(temp_dir):
            try:
                import shutil
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                self.log(">>> [系统系统] 已自动清理 temp/ 文件夹里的历史截图缓存。")
            except Exception as e:
                self.log(f">>> [系统系统] 清理 temp/ 缓存失败: {e}")

    def closeEvent(self, event):
        """窗口关闭时自动触发的清理事件"""
        self.log("程序准备退出，正在执行安全清理...")
        # 1. 安全关闭后台可能正在跑的线程
        if self.task_thread and self.task_thread.is_running:
            self.task_thread.stop()
        
        # 2. 关闭前清理垃圾文件
        self.clean_temp_dir()
        
        # 3. 同意窗体关闭
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())