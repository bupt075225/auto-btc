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
max_buy_price=0
transaction_count=0
transaction_amount=45

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
    response = HuobiService.getAccountInfo(ACCOUNT_INFO)
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
    global latest_buy_order_id
    global transaction_count

    response = HuobiService.buyMarket(BITCOIN,amount,None,None,BUY_MARKET)
    #print response
    if response != None and response['result']=='success':
        latest_buy_order_id = response['id']
        transaction_count += 1
        logging.info('第%d次以市价买入成功' % transaction_count)
        return response['result']
    else:
        logging.warning('Error:buy BTC fail!')
        return None

'''
限价卖出
输入参数：
  price:限价卖出的价格(RMB为单位)
  amount:卖出BTC的数量
'''
def sell_btc(price, amount):
    global latest_sell_order_id

    response = HuobiService.sell(BITCOIN,price,amount,None,None,SELL)
    #print response
    if response != None and response['result']=='success':
        latest_sell_order_id=response['id']
        return response['result']
    else:
        logging.warning('Error:sell fail!')
        return None

'''
获取当前市价
'''
def get_current_price():
    response = HuobiService.get_realtime_price()
    if response != None:
        realtime_info = dict()
        #print response
        logging.info('当前人民币市场价格是 %f' % response['ticker']['last'])
        realtime_info['last'] = response['ticker']['last']
        realtime_info['high'] = response['ticker']['high']
        realtime_info['low'] = response['ticker']['low']
        return realtime_info
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
                #print response['processed_price'],self.order_type[response['type']],'状态是',self.order_status[response['status']]
                logging.info('%f %s 状态是 %s' % (float(response['processed_price']),self.order_type[response['type']],self.order_status[response['status']]))
                info['amount'] = float(response['processed_amount']) / float(response['processed_price'])
            elif response['type']==2:
                #print response['order_price'],self.order_type[response['type']],'状态是',self.order_status[response['status']]
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
买入条件判断
'''
def can_buy():
    result = False

    realtime = get_current_price()
    if realtime != None and float(realtime['last']) < max_buy_price:
        logging.info('当前市场价%f低于设置的最高买入价%f' % (float(realtime['last']), max_buy_price))
        result = True
    else:
        logging.info('当前市场价%f高于设置的最高买入价%f' % (float(realtime['last']), max_buy_price))
        result = False
        update_max_buy_price(float(realtime['high']),float(realtime['low']))
        # 第一个条件不满足立即返回
        return result

    last_order = order(latest_sell_order_id)
    order_info = last_order.get_order_info()
    if order_info != None and order_info['status'] == 2:
        print order_info
        print order_info['status']
        print order_info['order_price']
        result = True
    else:
        result = False

    return result

'''
一买一卖是一次完整的交易
'''
def do_transaction():
    # 买入
    ret = buy_btc_market(transaction_amount)
    if ret=='success':
        buy_order = order(latest_buy_order_id)
        info = buy_order.get_order_info()
        sell_price = float(info['processed_price']) + 1
        # 浮点数精确到小数点后4位
        sell_amount = round(info['amount'],4)
        if sell_price!=0 and sell_amount!=0:
           # 卖出
           ret = sell_btc(sell_price,sell_amount)
           if ret=='success':
               logging.info('以 %f 限价卖出 %f BTC委托成功' % (sell_price,sell_amount))
               return ret
           else:
               logging.info('以 %f 限价卖出 %f BTC委托失败' % (sell_price,sell_amount))
               return ret
    else:
        logging.warning('以市场价买入失败')
        return ret


def main():
    #get_sell_orders()
    #print get_current_price()
    #get_asset_info()
    logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(message)s')
    while 1:
        if transaction_count==0:
            global max_buy_price

            realtime = get_current_price()
            middle = (realtime['high'] - realtime['low']) / 2 + realtime['low']
            # 初始化最大买入价格
            max_buy_price = middle
            asset = get_asset_info()
            print float(asset['available_cny'])
            if asset != None and float(asset['available_cny']) > transaction_amount * 2 and realtime['last'] < max_buy_price:
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

if __name__ == "__main__":
    main()

