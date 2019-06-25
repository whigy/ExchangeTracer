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
import requests

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

def get_audios(url):
    browser = openBrowser(url)
    for i in range(1, 193):
        print(i)
        link = browser.find_element_by_link_text(str(i)).get_attribute('href')
        #link = "http://www4.nok.se/laromedel/rivstart/{:d}.mp3".format(i)
        with open("{:d}.mp3".format(i), "wb") as f:
            f.write(requests.get(link).content)
        
  

if __name__ == "__main__":
    logging.info("Start!")
    get_audios("https://www3.nok.se/-Settings-/Digitala-laromedel/Tjanster-ny/-R-/-Rivstart-/Extramaterial/")
    logging.info("The end of the script!")
