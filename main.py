###### IMPORTING NEEDED LIBRARIES
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
from twisted.internet import reactor
import config
import time
from statistics import mean
### IMPORTING CONFIG SO API AND SECRET CODE CAN BE STORED IN A DIFFERENT FILE AND CAN BE "SECURE"
### THERE IS ALSO A WAY TO STORE THEM AS AN OS VARIABLES OR JUST WRITE THEM IN THIS FILE AS VARIABLES


### CREATING CLIENT OBJECT
client = Client(config.api_key, config.api_secret)

###### CHANGING BINANCE LIBRARY VARIABLE TO TEST FOR MY TEST ACCOUNT
#client.API_URL = 'https://testnet.binance.vision/api'

### VARIABLES NEEDED FOR GETTING BTC PRICE USING WEBSOCKET
btc_price = {'error':False}
bitc = [0]
quantity = 0




######## GET BTC PRICE USING WEBSOCKET, ADD BTC PRICE VALUE TO AN ARRAY
def btc_trade_history(msg):

    if msg['e'] != 'error':
        ### APPEND VALUE TO THE ARRAY TO USE IT LATER AS THE LAST BTC PRICE
        bitc.append(float(msg['c']))
        ### DELETING SOME BTC VALUES FROM THE BEGGINING SO THE ARRAY DOESNT GET TOO BIG
        bitc.pop(0)
        btc_price['last'] = msg['c']
        btc_price['bid'] = msg['b']
        btc_price['last'] = msg['a']
    else:
        btc_price['error'] = True


########### GET MOVING AVERAGE FOR LAST 9 5M CANDLESTICKS, RETURN MA VALUE
def get_current_ma():

    bars = client.get_historical_klines('BTCUSDT', '5m',"45 min ago UTC" )
    close_arr = []
    ### GETTING ONLY "CLOSE" VALUES, BECAUSE WE ARE CALCULATING MA ONLY BASED ON "CLOSE" VALUES
    for line in bars:
        arr_add = line[4]
        close_arr.append(float(arr_add))
    current_ma = mean(close_arr)

    return current_ma




########### COMPARE MA TO BTC USING TO PARAMETERES, SO WE CAN GET UPDATED VALUE EVERY TIME WE CALL THE FUNCTION
########### RETURNING 1 IF MA>BTC, 2 IF MA<BTC AND 3 IF THEY ARE EQUAL(ALMOST NEVER, BUT I DID IT JUST IN CASE)
def compare_ma_btc(ma,btc):

    ret =0
    if ma > btc:
        print("ma > btc, should buy")
        ret = 1
    elif ma <btc:
        print("ma < btc, should sell")
        ret = 2
    elif ma == btc:
        print("Wait for the price to change a bit")
        ret =3
    return ret




### FUNCTION TO BUY GIVEN AMOUNT OF BTC USING MARKET ORDER
def buy_btc(qty):
    try:
        buy_order = client.create_order(symbol='ETHUSDT', side='BUY', type='MARKET', quantity=qty)
        print("buy order line")
    except BinanceAPIException as e:
    	# error handling goes here
        print(e)
    except BinanceOrderException as e:
    	# error handling goes here
        print(e)
    print("buy order complete")
### FUNCTION TO SELL GIVEN AMOUNT OF BTC USING MARKET ORDER
def sell_btc(qty):
    try:
            sell_order = client.create_order(symbol='ETHUSDT', side='SELL', type='MARKET', quantity=qty)
            print("sell order line")
    except BinanceAPIException as e:
    	# ERROR HANDLING
        print(e)
    except BinanceOrderException as e:
    	# ERROR HANDLING
        print(e)
    print("sell order complete")


####################### MAIN TWO FUNCTIONS WE ARE GOING TO USE ########################

########## FUNCTION TO OPEN A POSITION DEPENDING ON BTC AND MA (SELL OR BUY)
def open_pos():
    # order_opened VARIABLE LATER ON WILL SHOW THE TYPE OF THE POSITION IS OPENED
    # AND IT WILL BE USED TO DETERMINE HOW TO CLOSE THE POSITION
    # 0 = NO POSITION; 1 = BOUGHT, WAITING TO SELL; 2= SOLD, WAITING TO BUY; 3 = POSITION CLOSED, TASK FINISHED
    order_opened = 0
    quantity = input("Enter quantity of BTC to trade")
    # MAKING SURE QUANTITY IS A NUMBER
    while (quantity.isnumeric() == False):
        print("Please enter a number")
        quantity = input("Enter quantity of BTC to trade")
    # CHECKING IF ORDER HAS NOT BEEN FULFILLED YET
    if order_opened == 0:
        # IF'S TO DETERMINE WHETHER WE HAVE TO BUY OR SELL
        if compare_ma_btc(get_current_ma(),bitc[len(bitc)-1]) == 1:
            print("buying")
            buy_btc(quantity)
            order_opened =1
        elif compare_ma_btc(get_current_ma(),bitc[len(bitc)-1]) == 2:
            print("selling")
            sell_btc(quantity)
            order_opened =2
        elif compare_ma_btc(get_current_ma(),bitc[len(bitc)-1]) == 3:
            print("ma = btc price")
            order_opened = 3
    # RETURNING ORDER OPENED VALUE
    print("position opened")
    return order_opened

##### FUNCTION TO MAINTAIN POSITION, CHECK MA AND BTC PRICE VALUES IN REAL TIME AND TO CLOSE POSITION LATER ON
def maintain_pos():
    ### GETTING order_opened VALUE FROM open_pos() FUNCTION
    ### ALSO BY GETTING THIS VALUE THE open_pos FUNCTION GETS CALLED AND OPENS THE ORDER
    order_opened = open_pos()

    ### VALUE WE WILL NEED FOR LOOP CONDITION WHEN WE WILL BE WAITING FOR BTC PRICE TO CROSS MA
    ### IT WILL BE CHANGED TO FALSE AS SOON AS MA = BTC PRICE
    looop = True
    ### TWO IF STATEMENTS WITH WHILE LOOPS THAT FINISH WHEN MA = BTC
    ### AFTER MA = BTC AND WHEN WHILE LOOP IS OVER OUR POSITION IS CLOSED BUY DOING THE OPPOSITE ACTION WE DID WHEN WE OPENED A POSITION
    ### ALSO order_opened VALUE IS CHANGED TO "3" AFTER CLOSING THE POSITION
    if order_opened == 1:
        while looop:
            print("MA = ", get_current_ma())
            print("btc = ",bitc[len(bitc)-1])
            if (compare_ma_btc(get_current_ma(),bitc[len(bitc)-1]) != 1):
                looop = False
        sell_btc(quantity)
        order_opened = 3
        print("Position closed, sold btc")

    if order_opened == 2:
        while looop:
            print("MA = ", get_current_ma())
            print("btc = ",bitc[len(bitc)-1])
            if (compare_ma_btc(get_current_ma(),bitc[len(bitc)-1]) != 2):
                looop = False
        buy_btc(quantity)
        order_opened = 3
        print("Position closed, bought btc back")

    if order_opened == 3:
        print("Finished")


######## WEBSOCKET USAGE AND THIS IS WHERE WE CALL OUR MAIN FUNCTION

# CREATING WEBSOCKET VARIABLES
bsm = BinanceSocketManager(client)
conn_key = bsm.start_symbol_ticker_socket('BTCUSDT', btc_trade_history)
# STARTING WEBSOCKET
bsm.start()
# TIMEOUT SO BITCOIN PRICE ARRAY GETS SOME TIME TO GET FIRST VALUE
# (IT CRASHED A COUPLE TIMES WHILE I WAS TESTING, SO I HAD TO PUT IT HERE)
time.sleep(2)
# CALLING MAINTAIN FUNCTION FIRST BECAUSE IT CALLS open_pos() IN THE FIRST LINES OF ITS CODE
maintain_pos()


# STOPPING WEBSOCKET
bsm.stop_socket(conn_key)
# TERMINATING WEBSOCKET
reactor.stop()
