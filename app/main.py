import streamlit as st
import pandas as pd
import os
import json
import logging
from src.iex import IEXstock
from datetime import datetime, date, timedelta
from src.database.mongoDB import StockFundaDB

# helper function
def format_number(num):
    return f"{num:,}"

# Create a function to get the company name
def get_company_name(symbol):
    if symbol in stock_dict.keys():
        return stock_dict[symbol]

def createSentimentScore(news):
    """
    Pass each news into vader model,calculate their compound score
    :return: data frame for each news for its compound score
    """
    import nltk
    nltk.download("vader_lexicon")
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    sid = SentimentIntensityAnalyzer()

    resultScores = []
    newsHeadline = []
    newsDate = []

    for article in news:
        summary = article['summary'] if article['summary'] != "No summary available." else ""
        headline = article['headline']
        date = str(datetime.utcfromtimestamp(article['datetime']/1000).date())
        text = headline + " " + summary
        resultScores.append(sid.polarity_scores(text)["compound"])
        newsHeadline.append(headline)
        newsDate.append(date)
    result = pd.DataFrame({"date": newsDate,"headline": newsHeadline,"score": resultScores})
    return result

# client = redis.Redis(host="localhost", port=6379)

# logging.info(os.getcwd())
# get this file location
dir = os.path.dirname(__file__)

stock_market_option = st.sidebar.radio('Stock Market', ('US', 'HK'))

if stock_market_option == 'US':

    filename = os.path.join(dir, 'src', 'stock_names.json')
    with open(filename) as f:
        stock_dict = json.load(f)

    screen = st.sidebar.selectbox(
        "View", ('Overview', 'Fundamentals', 'News', 'Ownership', 'Strategy'), index=0)
    st.title(screen)

    symbol = st.sidebar.selectbox("Stock Symbol", list(stock_dict.keys()))

    failure = 1
    while failure:
        try:
            stock = IEXstock(os.environ["IEX_TOKEN"], symbol)
            failure = 0
        except Exception as e:
            logging.info(e)
else:
    filename = os.path.join(dir, 'src', 'hk_stock_name.json')
    with open(filename) as f:
        stock_dict = json.load(f)

    screen = st.sidebar.selectbox(
        "View", ('', 'Strategy'), index=0)
    st.title(screen)

    symbol = st.sidebar.selectbox("Stock Symbol", list(stock_dict.keys()))

if screen == 'Overview':
    fundaDB = StockFundaDB('projectValHubDB','stockFundaData',os.environ["MONGO_URL"])
    collection = fundaDB.connectDB()
    fundaDB.create_index(collection)

    logo_cache_key = f"{symbol}_logo"
    logo_cache = fundaDB.find_cache(collection, logo_cache_key)

    if logo_cache is not None:
        logging.info("found logo in cache")
        logo = logo_cache["data"]
    else:
        logging.info("getting logo from api, and then storing it in cache")
        logo = stock.get_logo()
        fundaDB.save_cache(collection, logo, logo_cache_key)

    company_cache_key = f"{symbol}_company"
    company_info_cache = fundaDB.find_cache(collection, company_cache_key)

    if company_info_cache is not None:
        logging.info("found company news in cache")
        company_info = company_info_cache["data"]
    else:
        logging.info("getting company from api, and then storing it in cache")
        company_info = stock.get_company_info()
        fundaDB.save_cache(collection, company_info, company_cache_key)

    col1, col2 = st.columns([1, 4])

    with col1:
        st.image(logo['url'])

    with col2:
        st.subheader(company_info['companyName'])
        st.write(company_info['industry'])
        st.subheader('Description')
        st.write(company_info['description'])
        st.subheader('CEO')
        st.write(company_info['CEO'])


elif screen == 'News':
    fundaDB = StockFundaDB('projectValHubDB','stockFundaData',os.environ["MONGO_URL"])
    collection = fundaDB.connectDB()
    fundaDB.create_index(collection)

    news_cache_key = f"{symbol}_news"
    news_cache = fundaDB.find_cache(collection, news_cache_key)

    if news_cache is not None:
        logging.info("found news in cache")
        news = news_cache["data"]
    else:
        news = stock.get_company_news()
        fundaDB.save_cache(collection, news, news_cache_key)

    scoreDf = createSentimentScore(news)

    st.subheader("Sentiment Analysis Results for Following News (-1 means extreme negative class, +1 means extreme positive class)")
    table = pd.DataFrame([{"Mean": scoreDf["score"].mean(), "Standard Deviation": scoreDf["score"].std(),
                           "Min":scoreDf["score"].min(), "Max":scoreDf["score"].max()
                           }], index= [""]
    )
    st.table(table)

    for article in news:
        st.subheader(article['headline'])
        dt = datetime.utcfromtimestamp(article['datetime']/1000).isoformat()
        st.write(f"Posted by {article['source']} at {dt}")
        st.write(article['url'])
        st.write(article['summary'])
        st.image(article['image'])


elif screen == 'Fundamentals':

    fundaDB = StockFundaDB('projectValHubDB','stockFundaData',os.environ["MONGO_URL"])
    collection = fundaDB.connectDB()
    fundaDB.create_index(collection)

    stats_cache_key = f"{symbol}_stats"
    stats_cache = fundaDB.find_cache(collection, stats_cache_key)

    if stats_cache is None:
        stats = stock.get_stats()
        fundaDB.save_cache(collection, stats, stats_cache_key)
    else:
        logging.info("found stats in cache")
        stats = stats_cache["data"]

    st.header('Ratios')

    col1, col2 = st.columns(2)

    with col1:
        st.subheader('P/E')
        st.write(stats['peRatio'])
        st.subheader('Forward P/E')
        st.write(stats['forwardPERatio'])
        st.subheader('PEG Ratio')
        st.write(stats['pegRatio'])
        st.subheader('Price to Sales')
        st.write(stats['priceToSales'])
        st.subheader('Price to Book')
        st.write(stats['priceToBook'])
    with col2:
        st.subheader('Revenue')
        st.write(format_number(stats['revenue']))
        st.subheader('Cash')
        st.write(format_number(stats['totalCash']))
        st.subheader('Debt')
        st.write(format_number(stats['currentDebt']))
        st.subheader('200 Day Moving Average')
        st.write(stats['day200MovingAvg'])
        st.subheader('50 Day Moving Average')
        st.write(stats['day50MovingAvg'])

    fundamentals_cache_key = f"{symbol}_fundamentals"
    fundamentals_cache = fundaDB.find_cache(collection, fundamentals_cache_key)

    if fundamentals_cache is None:
        fundamentals = stock.get_fundamentals('quarterly')
        fundaDB.save_cache(collection, fundamentals, fundamentals_cache_key)
    else:
        logging.info("found fundamentals in cache")
        fundamentals = fundamentals_cache["data"]

    for quarter in fundamentals:
        st.header(f"Q{quarter['fiscalQuarter']} {quarter['fiscalYear']}")
        st.subheader('Filing Date')
        st.write(quarter['filingDate'])
        st.subheader('Revenue')
        st.write(format_number(quarter['revenue']))
        st.subheader('Net Income')
        st.write(format_number(quarter['incomeNet']))

    st.header("Dividends")

    dividends_cache_key = f"{symbol}_dividends"
    dividends_cache = fundaDB.find_cache(collection, dividends_cache_key)

    if dividends_cache is None:
        dividends = stock.get_dividends()
        fundaDB.save_cache(collection, dividends, dividends_cache_key)
    else:
        logging.info("found dividends in cache")
        dividends = dividends_cache["data"]

    for dividend in dividends:
        st.write(dividend['paymentDate'])
        st.write(dividend['amount'])

elif screen == 'Ownership':

    st.subheader("Institutional Ownership")

    fundaDB = StockFundaDB('projectValHubDB','stockFundaData',os.environ["MONGO_URL"])
    collection = fundaDB.connectDB()
    fundaDB.create_index(collection)

    institutional_ownership_cache_key = f"{symbol}_institutional"
    institutional_ownership_cache = fundaDB.find_cache(collection, institutional_ownership_cache_key)

    if institutional_ownership_cache is None:
        institutional_ownership = stock.get_institutional_ownership()
        fundaDB.save_cache(collection, institutional_ownership, institutional_ownership_cache_key)

    else:
        logging.info("getting inst ownership from cache")
        institutional_ownership = institutional_ownership_cache["data"]

    for institution in institutional_ownership:
        st.write(institution['date'])
        st.write(institution['entityProperName'])
        st.write(institution['reportedHolding'])

    st.subheader("Insider Transactions")

    insider_transactions_cache_key = f"{symbol}_insider_transactions"
    insider_transactions_cache = fundaDB.find_cache(collection, insider_transactions_cache_key)

    if insider_transactions_cache is None:
        insider_transactions = stock.get_insider_transactions()
        fundaDB.save_cache(collection, insider_transactions, insider_transactions_cache_key)
    else:
        logging.info("getting insider transactions from cache")
        insider_transactions = insider_transactions_cache["data"]

    for transaction in insider_transactions:
        st.write(transaction['filingDate'])
        st.write(transaction['fullName'])
        st.write(transaction['transactionShares'])
        st.write(transaction['transactionPrice'])

elif screen == 'Strategy':
    from src.StreamStrat import run
    run(stock_market_option, symbol, get_company_name(symbol))

elif screen == "":
    from src.database.mongoDB import StockPriceDB
    from bokeh.plotting import figure
    from bokeh.models import ColumnDataSource, HoverTool

    dbName = 'projectValHubDB'
    colName = 'hkStockPriceData'

    stockPriceDB = StockPriceDB(dbName, colName, os.environ["MONGO_URL"], stock_market_option)
    collection = stockPriceDB.connectDB()
    stockPriceDB.create_index(collection)

    # download the data
    today = date.today()
    oneMonthAgo = today - timedelta(days=30)

    stockPriceDB.get_data(collection, symbol, oneMonthAgo, today)

    ## get data from db
    df = stockPriceDB.load_data(collection, symbol, oneMonthAgo, today)

    company_name = get_company_name(symbol)

    source1 = ColumnDataSource(data=df)
    # plot for close recent month
    closePlotObj = figure(x_axis_type="datetime", plot_height=350)
    closePlotObj.line(x='index', y='Close', source=source1, line_width=4)
    closePlotObj.xaxis.axis_label = 'Date'
    closePlotObj.yaxis.axis_label = f'Close Price {stock_market_option}D'

    closePlotObj.add_tools(
        HoverTool(
            tooltips=[('date', '@index{%F}'), ('close', '$@Close{0.2f}')],
            formatters={
                '@index': 'datetime'
            },
            mode="vline"
        )
    )

    # plot for volume recent month
    source2 = ColumnDataSource(data=df)
    volumePlotObj = figure(x_axis_type="datetime", plot_height=350)
    volumePlotObj.line(x='index', y='Volume', source=source2, line_width=4)
    volumePlotObj.xaxis.axis_label = 'Date'
    volumePlotObj.yaxis.axis_label = f'Volume {stock_market_option}D'

    volumePlotObj.add_tools(
        HoverTool(
            tooltips=[('date', '@index{%F}'), ('volume', '@Volume{0.00 a}')],
            formatters={
                '@index': 'datetime'
            },
            mode="vline"
        )
    )

    # Display the close prices
    st.header(company_name+" Close Price\n")
    #st.line_chart(df['Close'])
    st.bokeh_chart(closePlotObj, use_container_width=True)
    # Display the volume
    st.header(company_name+" Volume\n")
    st.bokeh_chart(volumePlotObj, use_container_width=True)
    #st.line_chart(df['Volume'])
