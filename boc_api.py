from bocfx import bocfx
import logging
from datetime import date, timedelta, datetime
import pandas as pd
import pickle
import sys
import os
import base64

from google.cloud import storage
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition, ContentId

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
TIME_FORMAT = "%Y-%m-%d"


def upload_to_gs(bucket, object_path):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket)
    gcs_path = object_path.split("/")[-1]
    blob = bucket.blob(gcs_path)
    with open(object_path, "rb") as file_obj:
        blob.upload_from_file(file_obj)


def download_from_gs(bucket, object_path):
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket)
    gcs_path = object_path.split("/")[-1]
    blob = bucket.blob(gcs_path)
    with open(object_path, "wb") as file_obj:
        blob.download_to_file(file_obj)


def send_email(email, file):
    today = datetime.today().strftime("%Y%m%d")
    with open(file, 'r') as f:
        data = f.readlines()
        today = data[-1].strip("\n").split(" ")
        yesterday = data[-2].strip("\n").split(" ")

    message = Mail(
        from_email="huijie.wang@devoteam.com",
        to_emails=["whigy@outlook.com"],
        subject='ExchangeTracer-{}'.format(today[0]),
        html_content='''
            <strong>BOC info</strong>\n\n
            <i>Yesterday (full data): {}</i>\n\n
            <i>Opening: {}</i>\n\n
            <i>Max: {}</i>\n\n
            <i>Min: {}</i>\n\n
            <i>Closing: {}</i>\n\n\n\n
            <i>Today(Newest): {}</i>\n\n
            <i>Opening: {}</i>\n\n
            <i>Max: {}</i>\n\n
            <i>Min: {}</i>\n\n
            <i>Closing: {}</i>'''.format(
                yesterday[0], yesterday[1], yesterday[2], yesterday[3], yesterday[4],
                today[0], today[1], today[2], today[3], today[4]
        )
    )

    with open(file, 'r') as f:
        string_csv = f.read()

    with open(file, 'r') as f:
        string_csv = f.read()

    file_name = 'output-{}.txt'.format(today)
    b64data = base64.b64encode(bytes(string_csv, 'utf-8'))
    attachment = Attachment()
    attachment.file_content = FileContent(str(b64data, 'utf-8'))
    attachment.file_name = FileName(file_name)
    message.attachment = attachment

    try:
        sendgrid_client = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sendgrid_client.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

    print('Done')


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
            names=["date", "opening", "max", "min", "closing"])

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
            BUCKET=
            OUTPUT=output/bocfx_output.txt
            CURRENCY=SEK
            START=YESTERDAY
            END=AUTO
        """)
    try:
        if parameters["BUCKET"] != '':
            download_from_gs(parameters["BUCKET"], parameters["OUTPUT"])
        with open(parameters["OUTPUT"], 'r') as f:
            d = f.readlines()[-1].strip("\n").split(" ")
    except Exception as e:
        logging.info("No output data exist! {}".format(e))
        raise
    if parameters["START"] == "YESTERDAY":
        parameters["START"] = (datetime.today() - timedelta(1))
    elif parameters["START"] == "AUTO":
        parameters["START"] = datetime.strptime(d[0].replace("/", "-"), TIME_FORMAT)
    if parameters["END"] == "TODAY":
        parameters["END"] = datetime.today()

    parameters["TIME"] = (parameters["END"] - parameters["START"]).days + 1

    return parameters


def main(event=None, callback=None):
    logging.info("Start!")
    p = readConfig()
    logging.info("CURRENCY {}, Start time: {}, End time: {}, loading data... Waiting....".format(
        p["CURRENCY"], p["START"].strftime(TIME_FORMAT), p["END"].strftime(TIME_FORMAT)
    ))
    r = bocfx(p["CURRENCY"], 'SE,ASK', time=p["TIME"])
    calculateData(r, p["OUTPUT"])
    if p["BUCKET"] != '':
        upload_to_gs(p["BUCKET"], p["OUTPUT"])
    send_email(p['EMAIL'], p['OUTPUT'])
    logging.info("The end of the script!")


if __name__ == "__main__":
    main()
