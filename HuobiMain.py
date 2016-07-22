#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import sys
import time
import math
import logging

sys.path.append('/home/workDir/hubi/demo_python-master/')
from huobi.Util import *
from huobi import HuobiService

latest_sell_order_id=None
latest_buy_order_id=None
lowest_buy_order_id=None
max_buy_price=0
transaction_count=0
transaction_amount=45
last_low_price=0


'''
最近10次交易记录
'''
def latest_deal_orders():
    response = HuobiService.getNewDealOrders(1,NEW_DEAL_ORDERS)
    print response

'''
获取委托交易信息
'''
def get_sell_orders():
    response = HuobiService.getOrders(1,GET_ORDERS)
    print response

'''
获取个人资产信息
'''
def get_asset_info():
    try:
        response = HuobiService.getAccountInfo(ACCOUNT_INFO)
    except ConnectionError as e:
        logging.error(e)
        return None

    if response != None:
        #print response
        asset = dict()
        logging.info('可用现金%f' % float(response['available_cny_display']))
        asset['available_cny'] = response['available_cny_display']
        return asset
    else:
        logging.error('获取资产信息失败')
        return None
'''
以市价买入
输入参数：
  amount:买入总金额(RMB为单位)
'''
def buy_btc_market(amount):
    response = HuobiService.buyMarket(BITCOIN,amount,None,None,BUY_MARKET)
    #print response
    if response != None and response['result']=='success':
        info = dict()
        info['id'] = response['id']
        info['result'] = response['result']
        count = transaction_count + 1
        logging.info('第%d次以市价买入成功' % count)
        return info
    else:
        logging.warning('Error:buy BTC fail!')
        return None

'''
以市价卖出
  amount:卖出BTC的数量
'''
def sell_btc_market(amount):
    response = HuobiService.sellMarket(BITCOIN,amount,None,None,SELL_MARKET)
    print response
    if response != None and response['result']=='success':
        info = dict()
        info['id'] = response['id']
        info['result'] = response['result']
        return info
    else:
        logging.error('Error:sell BTC fail by market price')
        return None

'''
限价卖出
输入参数：
  price:限价卖出的价格(RMB为单位)
  amount:卖出BTC的数量
'''
def sell_btc(price, amount):
    response = HuobiService.sell(BITCOIN,price,amount,None,None,SELL)
    #print response
    if response != None and response['result']=='success':
        info = dict()
        info['id'] = response['id']
        info['result'] = response['result']
        return info
    else:
        logging.error('Error:sell fail!')
        return None

'''
获取当前市价
'''
def get_current_price():
    try:
        response = HuobiService.get_realtime_price()
    except ConnectionError, e:
        logging.exception(e)
        return None

    if response != None:
        realtime = dict()
        #print response
        realtime['last'] = response['ticker']['last']
        realtime['high'] = response['ticker']['high']
        realtime['low'] = response['ticker']['low']
        logging.info('当前人民币市场价格是%f,最低价%f,最高价%f' % (realtime['last'],realtime['low'],realtime['high']))
        return realtime
    else:
        logging.warning('Error:get realtime price fail!')
        return None

class order(object):
    def __init__(self, order_id):
        self.order_status = {0:'未成交', 1:'部分成交', 2:'已完成', 3:'已取消', 5:'异常', 7:'队列中'}
        self.order_type = {1:'限价买', 2:'限价卖', 3:'市价买', 4:'市价卖'}
        self.order_id = order_id

    def get_order_info(self):
        response = HuobiService.getOrderInfo(BITCOIN,self.order_id,ORDER_INFO)
        if response != None:
            #print response
            info = dict()
            # 限价单的委托价
            info['order_price'] = response['order_price']
            # 成交价格
            info['processed_price'] = response['processed_price']
            info['status'] = response['status']
            if response['type']==3:
                # 市价买单
                logging.info('%f %s 状态是 %s' % (float(response['processed_price']),self.order_type[response['type']],self.order_status[response['status']]))
                info['amount'] = float(response['processed_amount']) / float(response['processed_price'])
            elif response['type']==2:
                # 限价卖单
                logging.info('%s %s 状态是 %s' % (float(response['order_price']),self.order_type[response['type']],self.order_status[response['status']]))
                info['amount'] = response['order_amount']
            return info
        else:
            logging.warning('Error:get order info fail!')
            return None

'''
检查是否需要更新最高买入价
'''
def update_max_buy_price(high,low):
    global max_buy_price

    middle = (high - low) / 2 + low
    if abs(middle - max_buy_price) > 15 and high - middle > 30:
        max_buy_price = middle
        logging.info('重新设置最高买入价为%f' % max_buy_price)

'''
追踪最高价记录的刷新
'''
def trace_high_price():
    global lowest_buy_order_id
    price_check_count=0

    if lowest_buy_order_id == None:
        logging.info('没有低价单可卖出')
        return

    while 1:
        realtime = get_current_price()
        if realtime != None and realtime['last'] - realtime['low'] > 30:
            # 高价被刷新,等待半分钟看是否继续被刷新
            logging.info('低价单可以在%f卖出' % realtime['last'])
            price_check_count += 1
            time.sleep(30)
            continue
        else:
            break

    if price_check_count > 0:
        # 在刷新后的最高价附近卖出
        buy_order = order(lowest_buy_order_id)
        info = buy_order.get_order_info()
        ret = sell_btc_market(info['amount'])
        if ret != None and ret['result']=='success':
            logging.info('在高价%f附近卖出成功' % realtime['last'])
            lowest_buy_order_id = None
        else:
            logging.error('在高价%f附近卖出失败' % realtime['last'])

'''
追踪最低价记录的刷新
'''
def trace_low_price():
    global last_low_price
    global lowest_buy_order_id
    price_check_count = 0
    interval = 180

    while 1:
        realtime = get_current_price()
        if realtime != None and float(realtime['low']) != last_low_price:
            # 最低价被刷新,等待3分钟看价格是否继续下迭
            logging.info('最低价%f被刷新为%f,最高价是%f' % (last_low_price, float(realtime['low']), float(realtime['high'])))
            last_low_price = float(realtime['low'])
            price_check_count += 1
            time.sleep(interval)
            # 价格持续下迭,加长观察时间
            interval += 180
            continue
        elif lowest_buy_order_id != None and realtime['last'] - realtime['low'] < 10:
            # 最低价没被刷新,也没有在最高价附近成功卖出,价格开始迭落,接近最低价前卖出
            logging.info('最低价没有被刷新,准备卖出最低价')
            buy_order = order(lowest_buy_order_id)
            info = buy_order.get_order_info()
            ret = sell_btc_market(info['amount'])
            if ret != None and ret['result']=='success':
                logging.info('在最低价%f附近甩卖成功' % last_low_price)
                lowest_buy_order_id = None
            else:
                logging.error('在最低价%f附近甩卖失败' % last_low_price)
            break
        else:
            break


    if price_check_count > 0 and lowest_buy_order_id==None and realtime['last'] - realtime['low'] < 20:
        price_check_count = 0
        # 在最低价附近买入
        rsp = buy_btc_market(transaction_amount)
        if rsp['result']=='success':
            lowest_buy_order_id = rsp['id']
        return rsp['result'];
        
'''
买入条件判断
'''
def can_buy():
    result = False

    realtime = get_current_price()
    if realtime==None:
        return result

    if abs(realtime['low'] - last_low_price) > 20:
        # 最低价发生突变,如0点时刻以市场价更新最低价,不适合交易
        logging('最低价发生突变从%f 变为 %f' % (last_low_price, realtime['low']))
        trace_low_price()
        return result

    if float(realtime['last']) < max_buy_price and lowest_buy_order_id!=None:
        # 在价格上涨阶段买卖,下迭阶段即使低于中值也不买入,否则容易高价位套住
        logging.info('当前市场价%f低于设置的最高买入价%f' % (float(realtime['last']), max_buy_price))
        result = True
    else:
        logging.info('当前市场价%f高于设置的最高买入价%f' % (float(realtime['last']), max_buy_price))
        if realtime['high'] - realtime['low'] < 20:
            logging.info('最高价与最低价价差小于20,可以买入')
            result = True
        else:
            update_max_buy_price(float(realtime['high']),float(realtime['low']))
            trace_high_price()
            result = False
            # 第一个条件不满足立即返回
            return result

    last_order = order(latest_sell_order_id)
    order_info = last_order.get_order_info()
    if order_info != None and order_info['status'] == 2:
        #print order_info
        #print order_info['status']
        #print order_info['order_price']
        result = True
    else:
        trace_low_price()
        result = False

    return result

'''
一买一卖是一次完整的交易
'''
def do_transaction():
    global latest_buy_order_id
    global transaction_count
    global latest_sell_order_id

    # 买入
    rsp = buy_btc_market(transaction_amount)
    if rsp['result']=='success':
        latest_buy_order_id = rsp['id']
        transaction_count += 1

        buy_order = order(latest_buy_order_id)
        info = buy_order.get_order_info()
        sell_price = float(info['processed_price']) + 1
        # 浮点数精确到小数点后4位
        sell_amount = round(info['amount'],4)
        if sell_price!=0 and sell_amount!=0:
           # 卖出
           rsp = sell_btc(sell_price,sell_amount)
           if rsp['result']=='success':
               latest_sell_order_id=rsp['id']
               logging.info('以 %f 限价卖出 %f BTC委托成功' % (sell_price,sell_amount))
               return rsp['result']
           else:
               logging.info('以 %f 限价卖出 %f BTC委托失败' % (sell_price,sell_amount))
               return rsp['result']
    else:
        logging.warning('以市场价买入失败')
        return rsp['result']


'''
开启自动交易模式
'''
def auto_transact():
    while 1:
        if transaction_count==0:
            global max_buy_price

            realtime = get_current_price()
            middle = (realtime['high'] - realtime['low']) / 2 + realtime['low']
            # 更新最大买入价格
            max_buy_price = middle
            asset = get_asset_info()
            #print float(asset['available_cny'])
            if asset != None and float(asset['available_cny']) > transaction_amount and realtime['last'] < max_buy_price:
                logging.info('初次以市场价%f买入' % realtime['last'])
                do_transaction()
            else:
                logging.info('可用金额不足或市场价高于最高可买入价%f,无法买入' % max_buy_price)
                time.sleep(120)
        elif can_buy():
            logging.info('现在立刻以市场价买入')
            do_transaction()
        else:
            logging.info('稍后再尝试买入')
            time.sleep(10)

def init_params():
    global last_low_price
    global max_buy_price
    global transaction_amount
    global transaction_count

    realtime = get_current_price()
    if realtime==None:
        logging.error('APP init fail')
        sys.exit()

    last_low_price = realtime['low']
    max_buy_price = (realtime['high'] - last_low_price) / 2
    asset = get_asset_info()
    if asset==None:
        logging.error('Get asset fail')
        sys.exit()
    transaction_amount=45
    #transaction_amount = float(asset['available_cny']) / 3
    transaction_count = 0

def main():
    #get_sell_orders()
    #print get_current_price()
    #get_asset_info()
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(message)s')
    init_params()
    try:
        auto_transact()
    except Exception, e:
        logging.exception(e)
    finally:
        auto_transact()

if __name__ == "__main__":
    main()
    logging.info('APP exit now')

