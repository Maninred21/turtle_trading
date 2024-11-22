from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                           QGridLayout, QLabel, QTableWidget, QTableWidgetItem, 
                           QHeaderView, QGroupBox, QFrame, QHBoxLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
import logging

logger = logging.getLogger(__name__)

class TurtleTraderGUI(QMainWindow):
    def __init__(self, trader):
        try:
            super().__init__()
            self.trader = trader
            self.init_ui()
        except Exception as e:
            logger.error(f"GUI 初始化失败: {str(e)}", exc_info=True)

    def init_ui(self):
        """初始化UI"""
        # 设置主窗口
        self.setWindowTitle('海龟交易系统 - 回测结果')
        self.setGeometry(100, 100, 1200, 800)
        
        # 设置全局字体
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f6fa;
            }
            QLabel {
                font-family: "Microsoft YaHei", "SimHei";
            }
            QGroupBox {
                font-family: "Microsoft YaHei", "SimHei";
            }
        """)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #cccccc;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
        """)
        layout.addWidget(self.tabs)
        
        # 创建各个标签页
        self.create_summary_tab()
        self.create_trades_tab()
        
        # 更新数据
        self.update_summary_info()
        self.update_trades_detail()

    def create_summary_tab(self):
        """创建交易概览标签页"""
        try:
            tab = QWidget()
            layout = QHBoxLayout()  # 使用水平布局
            layout.setSpacing(20)
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 创建账户信息组
            account_group = self.create_group_box("账户信息", [
                ("初始资金", f"¥{self.trader.initial_capital:,.2f}"),
                ("当前资金", f"¥{self.trader.cash:,.2f}"),
                ("持仓市值", "¥0.00"),
                ("账户总值", "¥0.00")
            ], "账户概况")
            layout.addWidget(account_group)
            
            # 创建交易统计组
            trade_group = self.create_group_box("交易统计", [
                ("股票名称", self.trader.stock_name or "-"),
                ("股票代码", self.trader.stock_code or "-"),
                ("总交易次数", str(len(self.trader.trades_history))),
                ("买入次数", "0"),
                ("卖出次数", "0"),
                ("当前持仓", str(len(self.trader.positions)))
            ], "交易数据")
            layout.addWidget(trade_group)
            
            # 保存引用
            self.account_group = account_group
            self.trade_group = trade_group
            
            tab.setLayout(layout)
            self.tabs.addTab(tab, "交易概览")
            
        except Exception as e:
            logger.error(f"创建交易概览标签页失败: {str(e)}", exc_info=True)

    def create_group_box(self, title, items, subtitle=""):
        """创建分组框"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                background-color: white;
                border: 2px solid #e1e1e1;
                border-radius: 10px;
                margin-top: 2em;
                font-size: 16pt;
                font-weight: bold;
                padding: 25px;
                min-width: 400px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 20px;
                padding: 0 10px;
                color: #2c3e50;
                background-color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        
        # 添加副标题
        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setStyleSheet("""
                font-size: 13pt;
                color: #7f8c8d;
                margin-bottom: 15px;
                padding-bottom: 15px;
                border-bottom: 1px solid #ecf0f1;
            """)
            layout.addWidget(subtitle_label)
        
        # 创建网格布局用于数据项
        grid = QGridLayout()
        grid.setSpacing(15)
        
        for i, (label_text, value_text) in enumerate(items):
            # 创建标签和值的容器
            container = QWidget()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(10, 5, 10, 5)
            
            # 创建标签
            label = QLabel(label_text)
            label.setStyleSheet("""
                font-size: 12pt;
                color: #34495e;
                font-weight: normal;
                padding: 5px;
            """)
            
            # 创建值标签
            value = QLabel(value_text)
            value.setStyleSheet("""
                font-size: 12pt;
                font-weight: bold;
                padding: 5px;
            """)
            
            # 设置特殊样式（比如盈亏颜色）
            if "资金" in label_text or "市值" in label_text or "总值" in label_text:
                if value_text.startswith("¥"):
                    value_num = float(value_text.replace("¥", "").replace(",", ""))
                    if value_num > self.trader.initial_capital:
                        value.setStyleSheet("""
                            font-size: 12pt;
                            font-weight: bold;
                            color: #27ae60;
                            padding: 5px;
                        """)
                    elif value_num < self.trader.initial_capital:
                        value.setStyleSheet("""
                            font-size: 12pt;
                            font-weight: bold;
                            color: #e74c3c;
                            padding: 5px;
                        """)
            
            # 设置对齐
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # 添加到容器
            container_layout.addWidget(label)
            container_layout.addWidget(value)
            
            # 添加到网格
            grid.addWidget(container, i, 0)
        
        layout.addLayout(grid)
        group.setLayout(layout)
        return group

    def create_trades_tab(self):
        """创建交易明细标签页"""
        try:
            tab = QWidget()
            layout = QVBoxLayout()
            layout.setContentsMargins(20, 20, 20, 20)
            
            # 创建表格
            table = QTableWidget()
            table.setColumnCount(10)
            table.setHorizontalHeaderLabels([
                "交易日期", "交易类型", "成交价格", "成交数量",
                "手续费", "交易盈亏", "信号类型", "止损价",
                "10日最低", "20日最高"
            ])
            
            # 设置表格样式
            table.setStyleSheet("""
                QTableWidget {
                    background-color: white;
                    gridline-color: #e1e1e1;
                    border: 2px solid #e1e1e1;
                    border-radius: 5px;
                }
                QTableWidget::item {
                    padding: 8px;
                    font-size: 11pt;
                }
                QHeaderView::section {
                    background-color: #f8f9fa;
                    padding: 12px;
                    border: none;
                    border-bottom: 2px solid #e1e1e1;
                    font-size: 11pt;
                    font-weight: bold;
                    color: #2c3e50;
                }
                QTableWidget::item:selected {
                    background-color: #e8f0fe;
                }
            """)
            
            # 设置表格属性
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.ResizeToContents)
            header.setStretchLastSection(True)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setVisible(False)
            
            layout.addWidget(table)
            tab.setLayout(layout)
            
            # 保存引用
            self.trades_table = table
            self.tabs.addTab(tab, "交易明细")
            
        except Exception as e:
            logger.error(f"创建交易明细标签页失败: {str(e)}", exc_info=True)

    def update_summary_info(self):
        """更新交易概览信息"""
        try:
            # 计算账户信息
            position_value = sum(pos.shares * pos.entry_price for pos in self.trader.positions)
            total_value = self.trader.cash + position_value
            
            # 更新账户信息
            self.update_group_info(self.account_group, [
                ("初始资金", f"¥{self.trader.initial_capital:,.2f}"),
                ("当前资金", f"¥{self.trader.cash:,.2f}"),
                ("持仓市值", f"¥{position_value:,.2f}"),
                ("账户总值", f"¥{total_value:,.2f}")
            ])
            
            # 更新交易统计
            buy_count = sum(1 for t in self.trader.trades_history if t.get('action') == 'BUY')
            sell_count = sum(1 for t in self.trader.trades_history if t.get('action') == 'SELL')
            
            self.update_group_info(self.trade_group, [
                ("股票名称", self.trader.stock_name or "-"),
                ("股票代码", self.trader.stock_code or "-"),
                ("总交易次数", str(len(self.trader.trades_history))),
                ("买入次数", str(buy_count)),
                ("卖出次数", str(sell_count)),
                ("当前持仓", str(len(self.trader.positions)))
            ])
            
        except Exception as e:
            logger.error(f"更新交易概览失败: {str(e)}", exc_info=True)

    def update_trades_detail(self):
        """更新交易明细"""
        try:
            if not hasattr(self, 'trades_table'):
                return
                
            trades = self.trader.trades_history
            self.trades_table.setRowCount(len(trades))
            
            for i, trade in enumerate(trades):
                # 设置行数据
                items = [
                    trade.get('date', '-'),
                    '买入' if trade.get('action') == 'BUY' else '卖出',
                    f"¥{trade.get('price', 0):,.2f}",
                    f"{trade.get('shares', 0):,}",
                    f"¥{trade.get('commission', 0):,.2f}",
                    f"¥{trade.get('profit', 0):,.2f}" if trade.get('profit') is not None else '-',
                    trade.get('type', '-'),
                    f"¥{trade.get('stop_loss', 0):,.2f}" if trade.get('stop_loss') is not None else '-',
                    f"¥{trade.get('ten_day_low', 0):,.2f}" if trade.get('ten_day_low') is not None else '-',
                    f"¥{trade.get('twenty_day_high', 0):,.2f}" if trade.get('twenty_day_high') is not None else '-'
                ]
                
                for j, item in enumerate(items):
                    cell = QTableWidgetItem(str(item))
                    cell.setTextAlignment(Qt.AlignCenter)
                    
                    # 设置买卖单元格的背景色
                    if j == 1:  # 交易类型列
                        if trade.get('action') == 'BUY':
                            cell.setBackground(QColor('#ffebee'))  # 浅红色背景
                            cell.setForeground(QColor('#e74c3c'))  # 红色文字
                        else:
                            cell.setBackground(QColor('#e8f5e9'))  # 浅绿色背景
                            cell.setForeground(QColor('#27ae60'))  # 绿色文字
                    
                    # 设置盈亏的背景色
                    if j == 5 and trade.get('profit') is not None:  # 交易盈亏列
                        profit = trade.get('profit', 0)
                        if profit > 0:
                            cell.setBackground(QColor('#e8f5e9'))  # 浅绿色背景
                            cell.setForeground(QColor('#27ae60'))  # 绿色文字
                        elif profit < 0:
                            cell.setBackground(QColor('#ffebee'))  # 浅红色背景
                            cell.setForeground(QColor('#e74c3c'))  # 红色文字
                    
                    self.trades_table.setItem(i, j, cell)
                    
        except Exception as e:
            logger.error(f"更新交易明细失败: {str(e)}", exc_info=True)

    def update_group_info(self, group, items):
        """更新组件信息"""
        if not group or not group.layout():
            return
            
        grid = group.layout().itemAt(1).layout()  # 获取网格布局
        
        for i, (_, value) in enumerate(items):
            container = grid.itemAtPosition(i, 0).widget()
            if container:
                value_label = container.layout().itemAt(1).widget()
                if value_label:
                    value_label.setText(str(value))
