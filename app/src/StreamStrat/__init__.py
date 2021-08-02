import os
import pymongo
import streamlit as st
import pandas as pd
from PIL import Image
from ..iex import IEXstock
from ..quandl import QuandlStock
from datetime import timedelta,date

from .back_testing.DEMA import DoubleExponentialMovingAverage
from .back_testing.OBV import OnBalanceVolume
from .back_testing.SMA import SimpleMovingAverage
from .back_testing.fibonacci import FibonacciRetracementLevels
# from config import mongo_connect_str,IEX_TOKEN


# helper function
def datetime2str(time):
    return time.strftime('%Y-%m-%d')

def process_iex_data(dict1):
    df = pd.DataFrame(dict1)
    df = df[['date', 'uclose', 'uhigh', 'ulow', 'uopen', 'fclose', 'uvolume', 'symbol']]
    df['date'] = pd.to_datetime(df['date'], unit='ms').apply(datetime2str)
    df.set_axis(['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume', 'symbol'], axis='columns', inplace=True)
    df['date_obj'] = pd.to_datetime(df['Date'])
    return df

def process_quandl_data(symbol,list2d):
    ## supress warning
    pd.options.mode.chained_assignment = None

    data = pd.DataFrame(list2d)
    df = data[[0, 7, 8, 1, 9, 10]]
    df.set_axis(['Date', 'High', 'Low', 'Close', 'Previous Close', 'Volume'], axis='columns', inplace=True)
    df["Volume"] = df["Volume"] * 1000
    df['Date'] = pd.to_datetime(df['Date'])
    df['date_obj'] = pd.to_datetime(df['Date'])
    df["symbol"] = symbol
    return df

# ADD title and image
today = date.today()
threeYrsAgo = today - timedelta(days=3*365)


# Create a function to get user input
def get_input(stock_market_option):
    start_date = st.sidebar.date_input("Start date", threeYrsAgo)
    end_date = st.sidebar.date_input("End date", today)

    if stock_market_option == "US":
        strategy_choices = ('DEMA', 'OBV', 'SMA','Fibonacci')
    else:
        strategy_choices = ('DEMA', 'OBV', 'Fibonacci')
    selected_strategy = st.sidebar.selectbox('Chosen strategy', strategy_choices)
    stake = st.sidebar.number_input('Stake', min_value=1, max_value=None, value= 1000)
    cash = st.sidebar.number_input('Cash',  min_value=1, max_value=None, value= 100000 )

    return start_date, end_date, selected_strategy, stake, cash

# Create a function to get the company price data and selected timeframe

# def get_data(symbol, start, end):
#
    # Load the data
#    if symbol in stock_dict.keys():
#        df = pd.read_csv(f"data/{symbol}.csv")
#    else:
#        "Not Found"

    # Get the data range
#    #start = pd.to_datetime(start)
#    #end = pd.to_datetime(end)

#    # Set the start and end index row to 0
#    start_row = 0
#    end_row = 0

    # Match the user selection (date) to the date in dataset (search start date)
#    for i in range(0, len(df)):
#        if start <= pd.to_datetime(df['Date'][i]):
#            start_row = i
#            break
    # Match the user selection (date) to the date in dataset (search end date)
#    for j in range(0, len(df)):
#        if end >= pd.to_datetime(df['Date'][len(df)-1-j]):
#            end_row = len(df)-1-j
#            break
    # Set the index to be the date
#    df.set_index(pd.DatetimeIndex(df['Date'].values),inplace= True)

#    return df.iloc[start_row:end_row + 1, :]

def get_data(stock_market_option,symbol, start, end):

    dbName = 'projectValHubDB'
    if stock_market_option == "US": colName = 'stockPriceData'
    else: colName = 'hkStockPriceData'

    dbConn = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = dbConn[dbName]
    collection = db[colName]
    # create index for query and sorting
    #collection.create_index([('symbol', 1),("date_obj",1)])

    if collection.count_documents({'symbol': symbol}) > 0:
        last = collection.find({'symbol': symbol}, {"_id": 0}).sort(
            "date_obj", -1).limit(1)
        startNew = list(last)[0]['Date']
        delta1 = timedelta(days=3)
        if (pd.to_datetime(end)-pd.to_datetime(startNew)) > delta1 and stock_market_option == "US" :
            stock = IEXstock(os.environ["IEX_TOKEN"], symbol)
            dict1 = stock.getOHLC(startNew, str(end))
            df = process_iex_data(dict1)
            collection.insert_many(df.to_dict('records'))

        elif(pd.to_datetime(end)-pd.to_datetime(startNew)) > delta1 and stock_market_option == "HK":
            stock = QuandlStock(os.environ["QUANDL_TOKEN"], symbol)
            list2d = stock.get_stock_price(startNew, str(end))
            df = process_quandl_data(symbol,list2d)
            collection.insert_many(df.to_dict('records'))

    else:
        if stock_market_option == "US":
            stock = IEXstock(os.environ["IEX_TOKEN"], symbol)
            ## get recent 2yrs data
            dict1 = stock.getOHLC(range = True)
            df = process_iex_data(dict1)
            collection.insert_many(df.to_dict('records'))
        else:
            stock = QuandlStock(os.environ["QUANDL_TOKEN"], symbol)
            list2d = stock.get_stock_price(str(threeYrsAgo), str(today))
            df = process_quandl_data(symbol,list2d)
            collection.insert_many(df.to_dict('records'))


def load_data(stock_market_option,symbol, start, end):
    dbName = 'projectValHubDB'

    if stock_market_option == "US": colName = 'stockPriceData'
    else: colName = 'hkStockPriceData'

    dbConn = pymongo.MongoClient(os.environ["MONGO_URL"])
    db = dbConn[dbName]
    collection = db[colName]
    # testing sorting
    table = collection.find({'symbol': symbol, "date_obj": {"$gte": pd.to_datetime(start), "$lt": pd.to_datetime(end)}
                             }, {"_id": 0, 'symbol': 0})
    df = pd.DataFrame(list(table))
    df.set_index("date_obj", drop=True, inplace=True)
    df.index.name = 'index'
    return df

def run(stock_market_option,symbol,company_name):
    st.write(f"""
    ## Stock Market Web Application 
    **Stock price data** , date range from {threeYrsAgo.strftime('%b %d, %Y')} to {today.strftime('%b %d, %Y')}
    """)

    # ADD side bar header
    st.sidebar.header('User Input')

    # Set the index to be the date
    start, end, chosen_strategy, stake ,cash = get_input(stock_market_option)
    # download the data
    get_data(stock_market_option,symbol, start, end)
    ## get data from db
    df = load_data(stock_market_option, symbol, start, end)

    # Display the close prices
    st.header(company_name+" Close Price\n")
    st.line_chart(df['Close'])

    # Display the volume
    st.header(company_name+" Volume\n")
    st.line_chart(df['Volume'])

    if chosen_strategy == 'DEMA':
        dema = DoubleExponentialMovingAverage(df, symbol, stake, cash)
        dema.run()
        plot_obj = dema.plotBuySell(stock_market_option)
        tradeResultPlot,tradeStats = dema.plotBackTesting()
    elif chosen_strategy == 'OBV':
        obv = OnBalanceVolume(df, symbol, stake, cash)
        obv.run()
        plot_obj = obv.plotBuySell(stock_market_option)
        tradeResultPlot, tradeStats = obv.plotBackTesting()
    elif chosen_strategy == 'SMA':
        sma = SimpleMovingAverage(df, symbol, stake, cash)
        sma.run()
        plot_obj = sma.plotBuySell(stock_market_option)
        tradeResultPlot, tradeStats = sma.plotBackTesting()
    elif chosen_strategy == 'Fibonacci':
        fibonacci = FibonacciRetracementLevels(df, symbol, stake, cash)
        fibonacci.run()
        plot_obj = fibonacci.plotBuySell(stock_market_option)
        tradeResultPlot, tradeStats = fibonacci.plotBackTesting()

    # handling case of no trade happened
    if tradeStats:
        st.bokeh_chart(plot_obj, use_container_width=True)

        #broker_fig = Image.open("broker_fig.png")
        #st.image(broker_fig, use_column_width=True)
        st.bokeh_chart(tradeResultPlot, use_container_width=True)

        # create trade stats table
        st.header('Trades Statistics')
        df_stats1 = pd.DataFrame(tradeStats['result1'])
        df_stats2 = pd.DataFrame(tradeStats['result2'])

        table1 = df_stats1.pivot(
            index=['id1', 'id2'], columns='col', values='val')
        table2 = df_stats2.pivot(
            index=['id1', 'id2'], columns='col', values='val')
        table1.sort_values(by='id1', ascending=False,
                           kind='heapsort', inplace=True)
        table2.sort_values(by='id1', ascending=False,
                           kind='heapsort', inplace=True)
        col1, col2 = st.beta_columns(2)
        with col1:
            st.table(table1)
        with col2:
            st.table(table2)
    else:
        st.bokeh_chart(plot_obj, use_container_width=True)
        st.markdown(
            "<h3 style='text-align: center;'><strong>No Closed Trade Happened.</strong></h3>", unsafe_allow_html=True)

# Get statistics on the data
#st.header('Data Statistics')
# st.write(df.describe())
