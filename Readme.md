# ExchangeTracer

A simple crawler for bank BOC tracing currency. 

## To start:
- pip install requirements.txt
- Download [ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/downloads) unzip to the root directory.
- Config file 'Config.txt', with template format:
```
URL=http://srh.bankofchina.com/search/whpj/search.jsp
CURRENCY=1320
START=YESTERDAY
END=TODAY
```
All the fields are mandatory.
- URL : address to the search page
- CURRENCY: 1320 is SEK
- START: ACCEPT 'YESTERDAY' or Date format 'YYYY-MM-DD'
- END: ACCEPT 'TODAY' or Date format 'YYYY-MM-DD'
