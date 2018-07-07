# -*- coding: utf-8 -*-
"""
Created on Sat Jul  7 13:04:35 2018

@author: whigy
"""

import logging
import time
import os
import pandas as pd
import pickle
import sys

from datetime import date, timedelta, datetime
from selenium import webdriver

logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def openBrowser(url):
    browser = webdriver.Chrome(executable_path=os.path.join(os.getcwd(), 'chromedriver'))
    time.sleep(3)

    logging.info("Get URL {:s}".format(url))
    browser.get(url)
    logging.info("Brower ready.")
    return browser


def get_exchange(url, currency, startTime=None, endTime=None):
    browser = openBrowser(url)

    logging.info("Parsing BOC Webpage...")
    time.sleep(8)

    ########################## Search ################################
    # Send dates
    def clickCalendar(date):
        d = date.split("-")
        browser.find_element_by_xpath("//select[@id='calendarYear']/option[@value='{:s}']".format(d[0])).click()
        browser.find_element_by_xpath(
            "//select[@id='calendarMonth']/option[@value='{:d}']".format(int(d[1]) - 1)).click()
        browser.find_element_by_xpath("//table[@id='calendarTable']/tbody/tr/td[text()={:d}]".format(int(d[2]))).click()

    # end time
    if endTime == None:
        browser.find_element_by_name("nothing").click()
        browser.find_element_by_name("calendarToday").click()
        endTime = date.today().strftime("%Y-%m-%d")
    else:
        browser.find_element_by_name("nothing").click()
        clickCalendar(endTime)

    # Start time
    if startTime == None:  # if none: one day before end time
        startTime = (datetime.strptime(endTime, "%Y-%m-%d") - timedelta(1)).strftime("%Y-%m-%d")
    browser.find_element_by_name("erectDate").click()

    clickCalendar(startTime)

    # Send currency
    browser.find_element_by_xpath("//select[@id='pjname']/option[text()='{:s}']".format(currency)).click()
    browser.find_elements_by_class_name("search_btn")[1].click()

    logging.info("Searching {:s} from {:s} to {:s}.....".format(currency, startTime, endTime))

    time.sleep(3)

    ############################ Saving Information #######################################
    # Get pages
    try:
        pageSize = int(browser.find_element_by_class_name("turn_page").find_element_by_tag_name("li").text[1:-1])
    except Exception:
        logging.info("Page size regarded as less then 1.")
        pageSize = 1

    def turnPage():
        browser.find_element_by_class_name("turn_page").find_elements_by_tag_name("li")[-1].click()
        time.sleep(0.3)

    def findRows():
        def parseRow(row):
            tds = row.find_elements_by_tag_name("td")
            strList = [td.text for td in tds[1:-1]]
            strList += tds[-1].text.split(" ")
            return ','.join(strList) + '\n'

        rows = browser \
            .find_element_by_class_name("BOC_main") \
            .find_element_by_tag_name("table") \
            .find_elements_by_tag_name("tr")
        rowsText = [parseRow(row) for row in rows[1:-1]]
        return rowsText

    allRows = []
    if pageSize == 1:
        allRows = findRows()
    else:
        for i in range(pageSize):
            allRows += findRows()
            turnPage()

    logging.info("Collected {:d} rows data!".format(len(allRows)))

    header = "in_exc,in_cash,out_exc,out_cash,middle,boc_middle,date,time\n"

    filename = 'meta/{:s}_meta_{:s}.csv'.format(currency, datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(filename, 'w') as csvfile:
        csvfile.writelines(header)
        csvfile.writelines(allRows)
        csvfile.close()

    return filename


def calculateData(filename, output="output/output.txt"):
    with open(filename, 'rb') as file:
        df = pd.read_csv(file)

    histData = 'meta/history.pkl'
    if os.path.exists(histData):
        logging.info("Reading history data from {:s}".format(histData))
        try:
            with open(histData, 'rb') as f:
                data = pickle.load(f)
        except Exception as e:
            print('Unable to load data ', histData, ':', e)
            data = {}
    else:
        "History data not exist! Calculating from scratch!"
        data = {}

    group = df.sort_values(["date", "time"]) \
        .groupby("date")['out_exc'] \
        .aggregate({'opening': lambda x: x.iloc[0],
                    'max': 'max',
                    'min': 'min',
                    'closing': lambda x: x.iloc[-1]})
    data = {**data, **group.T.to_dict()}  # Update history
    with open(histData, 'wb') as f:
        pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    updated = pd.DataFrame.from_dict(data).T.reset_index()
    updated["date"] = updated["index"].apply(lambda x: x.replace(".", '/'))

    updated[["date", "opening", "max", "min", "closing"]]\
        .to_csv("output/output.txt", index=False, header=False, sep=" ")

def readConfig():
    parameters = {}
    try:
        with open("Config.txt", 'r') as f:
            for line in f:
                p = line.strip("\n").split("=")
                parameters[p[0]] = p[1]

    except Exception as e:
        print('Unable to load Configuration!')
        print("""
        Please create 'Congig.txt', with template:
            URL=http://srh.bankofchina.com/search/whpj/search.jsp
            CURRENCY=瑞典克朗
            START=YESTERDAY
            END=TODAY
        """)
    if parameters["START"] == "YESTERDAY":
        parameters["START"] = (date.today() - timedelta(1)).strftime("%Y-%m-%d")
    if parameters["END"] == "TODAY":
        parameters["END"] = date.today().strftime("%Y-%m-%d")

    return parameters

if __name__ == "__main__":
    logging.info("Start!")
    p = readConfig()
    filename = get_exchange(p["URL"], p["CURRENCY"], p["START"], p["END"])
    calculateData(filename)
    logging.info("The end of the script!")
