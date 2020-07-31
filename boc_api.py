from bocfx import bocfx
import logging
from datetime import date, timedelta, datetime
import pandas as pd
import pickle
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
TIME_FORMAT = "%Y-%m-%d"


def calculateData(result, output="output/output.txt"):
    # result: list: e.g. 
    #   [(1, 'SE_ASK', 'Time'), ('SEK', '80.67', '2020-07-31 20:13:26'),
    #    ('SEK', '80.67', '2020-07-31 20:13:07'), ('SEK', '80.67', '2020-07-31 20:07:58')]
    df = pd.DataFrame(result[1:], columns = ['CURRENCY' , 'SE_ASK', 'TIME'])
    df = df.drop('CURRENCY', axis=1)
    df['date'] = df["TIME"].apply(lambda x: x.split(" ")[0])
    group = df.sort_values(["date", "TIME"]) \
        .groupby("date")['SE_ASK'] \
        .aggregate({'opening': lambda x: x.iloc[0],
                    'max': 'max',
                    'min': 'min',
                    'closing': lambda x: x.iloc[-1]})
    
    reshape = group.reset_index()
    reshape["date"] = reshape["date"].apply(lambda x: x.replace("-", '/'))

    # read existing csv
    with open(output, 'rb') as file:
        origin = pd.read_csv(file, " ",
            names = ["date", "opening", "max", "min", "closing"])

    origin = origin[origin["date"] < reshape['date'].min()]
    updated = origin.append(reshape, ignore_index=True)

    logging.info("Update to file: {}".format(output))
    updated[["date", "opening", "max", "min", "closing"]]\
        .sort_values("date")\
        .to_csv(output, index=False, header=False, sep=" ")


def readConfig():
    parameters = {}
    try:
        with open("bocfx.config", 'r') as f:
            for line in f:
                p = line.strip("\n").split("=")
                parameters[p[0]] = p[1]
    except Exception as e:
        print('Unable to load Configuration!')
        print("""
        Please create 'bocfx.config', with template:
            OUTPUT=./output/output.txt
            CURRENCY=SEK
            START=YESTERDAY
            END=AUTO
        """)
    try:
        with open(parameters["OUTPUT"], 'r') as f:
            d = f.readlines()[-1].strip("\n").split(" ")
    except Exception as e:
        logging.info("No output data exist!")
    if parameters["START"] == "YESTERDAY":
        parameters["START"] = (datetime.today() - timedelta(1))
    elif parameters["START"] == "AUTO":
        parameters["START"] = datetime.strptime(d[0].replace("/", "-"), TIME_FORMAT)
    if parameters["END"] == "TODAY":
        parameters["END"] = datetime.today()

    parameters["TIME"] = (parameters["END"] - parameters["START"]).days + 1

    return parameters


if __name__ == "__main__":
    logging.info("Start!")
    p = readConfig()
    logging.info("CURRENCY {}, Start time: {}, End time: {}, loading data... Waiting....".format(
        p["CURRENCY"], p["START"].strftime(TIME_FORMAT), p["END"].strftime(TIME_FORMAT)
    ))
    r = bocfx(p["CURRENCY"], 'SE,ASK', time=p["TIME"])
    calculateData(r, p["OUTPUT"])
    logging.info("The end of the script!")