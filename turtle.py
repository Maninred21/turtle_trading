import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from PyQt5.QtWidgets import QApplication
import sys
from gui import TurtleTraderGUI

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

class BreakoutRecord:
    def __init__(self, date, price, N):
        self.date = date
        self.price = price
        self.N = N
        self.is_profitable = None  # None表示未确定，True表示盈利性，False表示亏损性
        self.max_price = price    # 记录突破后的最高价
        self.min_price = price    # 记录突破后的最低价

class TurtleTrader:
    def __init__(self, initial_capital=550000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = []  # 当前持仓
        self.trades_history = []  # 交易历史
        self.breakout_records = []  # 突破记录
        self.last_breakout = None   # 最后一次突破记录
        
        # 设置回测参数
        self.start_date = '20230101'
        self.end_date = '20241120'
        self.stock_code = '600611.SH'
        self.stock_name = None
        
        # 交易参数
        self.unit_limit = 4  # 最大持仓单位数
        
        # 设置Tushare
        ts.set_token('20240522230128-22019ddc-afa1-4905-89c9-8b822d27dc6b')
        self.pro = ts.pro_api()
        self.pro._DataApi__http_url = 'http://tsapi.majors.ltd:7000'
        
    def record_breakout(self, date, price, N):
        """记录新的突破"""
        breakout = BreakoutRecord(date, price, N)
        self.breakout_records.append(breakout)
        self.last_breakout = breakout
        return breakout

    def update_breakout_status(self, current_price, current_row):
        """更新突破状态"""
        if not self.last_breakout:
            return
            
        # 更新最高/最低价
        self.last_breakout.max_price = max(self.last_breakout.max_price, current_price)
        self.last_breakout.min_price = min(self.last_breakout.min_price, current_price)
        
        # 判断突破性质
        if self.last_breakout.is_profitable is None:
            # 检查是否发生2N不利变动（亏损性突破）
            if current_price <= (self.last_breakout.price - 2 * self.last_breakout.N):
                self.last_breakout.is_profitable = False
                logger.info(f"突破确认为亏损性 - 日期:{current_row['trade_date']} 价格:{current_price:.2f}")
            
            # 检查是否触及10日突破退出（盈利性突破）
            elif current_price < current_row['10_low']:
                self.last_breakout.is_profitable = True
                logger.info(f"突破确认为盈利性 - 日期:{current_row['trade_date']} 价格:{current_price:.2f}")

    def can_enter_trade(self):
        """判断是否可以入市"""
        if not self.breakout_records:
            return True  # 第一次突破，允许入市
        
        last_confirmed_breakout = next(
            (b for b in reversed(self.breakout_records[:-1]) 
             if b.is_profitable is not None), 
            None
        )
        
        if not last_confirmed_breakout:
            return True  # 没有已确认性质的突破，允许入市
            
        return not last_confirmed_breakout.is_profitable  # 如果上次是亏损性突破，允许入市

    def calculate_position_size(self, price, N):
        """计算头寸规模"""
        dollar_volatility = N * price
        position_size = (self.cash * 0.01) / dollar_volatility
        return int(position_size / 100) * 100  # 确保是100的整数倍

    def check_add_position(self, current_price, entry_price, N):
        """检查是否可以加仓"""
        if len(self.positions) >= self.unit_limit:
            return False
            
        price_increase = current_price - entry_price
        if price_increase >= 0.5 * N:
            return True
        return False

    def run_strategy(self):
        """运行交易策略"""
        logger.info(f"\n分析股票: {self.stock_code}")
        logger.info("-" * 50)
        
        # 获取股票名称
        try:
            stock_info = self.pro.stock_basic(ts_code=self.stock_code)
            self.stock_name = stock_info.iloc[0]['name'] if not stock_info.empty else "平安银行"
        except Exception as e:
            logger.error(f"获取股票名称失败: {str(e)}")
            self.stock_name = "平安银行"
        
        logger.info(f"股票名称: {self.stock_name}")
        logger.info(f"股票代码: {self.stock_code}")
        logger.info(f"回测周期: {self.start_date} - {self.end_date}")
        
        # 获取数据
        df = self.get_stock_data(self.stock_code)
        if df is None or len(df) < 20:
            logger.error("数据获取失败或数据量不足")
            return

        # 计算指标
        df['20_high'] = df['high'].rolling(window=20).max()
        df['20_low'] = df['low'].rolling(window=20).min()
        df['10_high'] = df['high'].rolling(window=10).max()
        df['10_low'] = df['low'].rolling(window=10).min()
        
        last_entry_price = None  # 记录最后一次入市价格
        
        # 遍历数据进行交易
        for i in range(20, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            current_price = current_row['close']
            current_date = current_row['trade_date']
            N = current_row['N']
            
            # 更新现有突破的状态
            self.update_breakout_status(current_price, current_row)
            
            # 检查20日突破
            if current_price > prev_row['20_high']:
                # 记录新的突破
                breakout = self.record_breakout(current_date, current_price, N)
                logger.info(f"检测到20日突破 - 日期:{current_date} 价格:{current_price:.2f}")
                
                # 判断是否可以入市
                if not self.positions and self.can_enter_trade():
                    # 计算头寸规模
                    shares = self.calculate_position_size(current_price, N)
                    if shares > 0:
                        self.enter_trade(current_date, current_price, shares, N)
                        last_entry_price = current_price
                        logger.info(f"入市交易 - 日期:{current_date} 价格:{current_price:.2f} 数量:{shares}")
            
            # 检查加仓条件
            elif self.positions and last_entry_price:
                if self.check_add_position(current_price, last_entry_price, N):
                    shares = self.calculate_position_size(current_price, N)
                    if shares > 0:
                        self.enter_trade(current_date, current_price, shares, N)
                        last_entry_price = current_price
                        logger.info(f"加仓交易 - 日期:{current_date} 价格:{current_price:.2f} 数量:{shares}")
            
            # 检查退出条件
            self.check_exits(current_price, current_date, current_row, N)

        logger.info(f"策略运行完成，共进行 {len(self.trades_history)} 次交易")

    def show_gui(self):
        """显示GUI界面"""
        try:
            app = QApplication(sys.argv)
            window = TurtleTraderGUI(self)
            window.show()
            sys.exit(app.exec_())
        except Exception as e:
            logger.error(f"GUI 显示失败: {str(e)}", exc_info=True)

    def get_stock_data(self, stock_code):
        """获取股票数据"""
        try:
            # 获取日线数据
            df = self.pro.daily(
                ts_code=stock_code,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            if df is None or df.empty:
                logger.error("获取数据失败")
                return None
            
            # 按日期排序
            df = df.sort_values('trade_date')
            
            # 计算真实波动幅度TR
            df['TR'] = df.apply(
                lambda x: max(
                    x['high'] - x['low'],
                    abs(x['high'] - x['pre_close']),
                    abs(x['low'] - x['pre_close'])
                ),
                axis=1
            )
            
            # 计算N值（20日TR平均值）
            df['N'] = df['TR'].rolling(window=20).mean()
            
            # 计算其他技术指标
            df['20_high'] = df['high'].rolling(window=20).max()
            df['20_low'] = df['low'].rolling(window=20).min()
            df['10_high'] = df['high'].rolling(window=10).max()
            df['10_low'] = df['low'].rolling(window=10).min()
            
            return df
            
        except Exception as e:
            logger.error(f"获取数据失败: {str(e)}")
            return None

    def enter_trade(self, date, price, shares, N):
        """执行入场交易"""
        try:
            commission = shares * price * 0.0003  # 手续费率0.03%
            
            # 记录交易
            trade = {
                'date': date,
                'action': 'BUY',
                'price': price,
                'shares': shares,
                'commission': commission,
                'type': '加仓' if self.positions else '首次入场',
                'stop_loss': price - 2 * N
            }
            self.trades_history.append(trade)
            
            # 更新持仓和现金
            position = Position(date, price, shares, price - 2 * N)
            self.positions.append(position)
            self.cash -= (shares * price + commission)
            
            return True
            
        except Exception as e:
            logger.error(f"入场交易失败: {str(e)}")
            return False

    def check_exits(self, current_price, current_date, current_row, N):
        """检查退出条件"""
        try:
            for pos in self.positions[:]:  # 使用切片创建副本以避免在迭代时修改列表
                # 检查止损
                if current_price < pos.stop_loss:
                    self.exit_trade(pos, current_date, current_price, '止损')
                    continue
                
                # 检查10日突破退出
                if current_price < current_row['10_low']:
                    self.exit_trade(pos, current_date, current_price, '10日突破')
                    continue
                
        except Exception as e:
            logger.error(f"检查退出条件失败: {str(e)}")

    def exit_trade(self, position, date, price, exit_type):
        """执行退出交易"""
        try:
            commission = position.shares * price * 0.0003
            profit = position.shares * (price - position.entry_price) - commission
            
            # 记录交易
            trade = {
                'date': date,
                'action': 'SELL',
                'price': price,
                'shares': position.shares,
                'commission': commission,
                'profit': profit,
                'type': exit_type
            }
            self.trades_history.append(trade)
            
            # 更新持仓和现金
            self.cash += (position.shares * price - commission)
            self.positions.remove(position)
            
            logger.info(f"{exit_type}退出 - 日期:{date} 价格:{price:.2f} 数量:{position.shares} 盈亏:{profit:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"退出交易失败: {str(e)}")
            return False

class Position:
    def __init__(self, entry_date, entry_price, shares, stop_loss):
        self.entry_date = entry_date
        self.entry_price = entry_price
        self.shares = shares
        self.stop_loss = stop_loss

if __name__ == '__main__':
    # 创建交易实例
    trader = TurtleTrader(initial_capital=550000)
    
    # 设置回测参数（可以根据需要修改）
    trader.start_date = '20230101'
    trader.end_date = '20241120'
    trader.stock_code = '600611.SH'
    
    # 运行策略
    trader.run_strategy()
    
    # 显示GUI
    trader.show_gui()
