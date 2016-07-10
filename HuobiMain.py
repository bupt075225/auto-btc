#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import sys
import time

sys.path.append('/home/workDir/hubi/demo_python-master/')
from huobi.Util import *
from huobi import HuobiService

latest_sell_order_id=None
latest_buy_order_id=None
max_buy_price=4345
transaction_count=0
transaction_amount=43

'''
最近10次交易记录
'''
def latest_deal_orders():
    response = HuobiService.getNewDealOrders(1,NEW_DEAL_ORDERS)
    print response

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
        print '第',transaction_count,'次以市场价买入成功'
        return response['result']
    else:
        print 'Error:buy BTC fail!'
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
        print 'Error:sell fail!'
        return None

'''
获取当前市价
'''
def get_current_price():
    response = HuobiService.get_realtime_price()
    if response != None:
        print response
        print '当前人民币市场价格是',response['ticker']['last']
        return response['ticker']['last']
    else:
        print 'Error:get realtime price fail!'
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
                print response['processed_price'],self.order_type[response['type']],'状态是',self.order_status[response['status']]
                info['amount'] = float(response['processed_amount']) / float(response['processed_price'])
            elif response['type']==2:
                print response['order_price'],self.order_type[response['type']],'状态是',self.order_status[response['status']]
                info['amount'] = response['order_amount']
            return info
        else:
            print 'Error:get order info fail!'
            return None

'''
买入条件判断
'''
def can_buy():
    result = False

    realtime_price = get_current_price()
    if realtime_price != None and realtime_price < max_buy_price:
        print '当前市场价',realtime_price,'低于设置的最高买入价',max_buy_price
        result = True
    else:
        print '当前市场价',realtime_price,'高于设置的最高买入价',max_buy_price
        result = False
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
        sell_amount = round(info['amount'],4)
        if sell_price!=0 and sell_amount!=0:
           # 卖出
           ret = sell_btc(sell_price,sell_amount)
           if ret=='success':
               print '以 %f 成功卖出 %f BTC' % (sell_price,sell_amount)
               return ret
           else:
               print '以 %f 卖出 %f BTC失败' % (sell_price,sell_amount)
               return ret
    else:
        print '以市场价买入失败'
        return ret


def main():
    while 1:
        if transaction_count==0:
            print '初次以市场价买入'
            do_transaction()
        elif can_buy():
            print '现在立刻以市场价买入'
            do_transaction()
        else:
            print '稍后再尝试买入'
            time.sleep(30)

if __name__ == "__main__":
    main()

