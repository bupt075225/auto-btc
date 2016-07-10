#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib
import hashlib
import hmac
import base64

#在此输入您的Key
ACCESS_KEY="52dc5fa3-d4d8d5d4-b1ef0fdc-aeba1"
SECRET_KEY="1d6e4680-c3c80834-9379e90a-b3ff5"

HUOBI_SERVICE_API="https://api.huobi.com/apiv3"
HUOBI_REALTIME_API="http://api.huobi.com/staticmarket/ticker_btc_json.js"

BUY = "buy"
BUY_MARKET = "buy_market"
CANCEL_ORDER = "cancel_order"
ACCOUNT_INFO = "get_account_info"
NEW_DEAL_ORDERS = "get_new_deal_orders"
ORDER_ID_BY_TRADE_ID = "get_order_id_by_trade_id"
GET_ORDERS = "get_orders"
ORDER_INFO = "order_info"
SELL = "sell"
SELL_MARKET = "sell_market"

BITCOIN = "1"

def signature(params):
    params = sorted(params.iteritems(), key=lambda d:d[0], reverse=False)
    message = urllib.urlencode(params)
    m = hashlib.md5()
    m.update(message)
    m.digest()
    sig=m.hexdigest()
    return sig

