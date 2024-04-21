import configparser
from email.message import EmailMessage
import smtplib
import ssl
import requests
from urllib.parse import urljoin
import datetime
import json
import dateutil.parser


def get_power_prices(price_area):
    BASE_URL = "https://www.hvakosterstrommen.no/api/v1/prices/"

    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)

    url = urljoin(
        BASE_URL,
        tomorrow.strftime(f"%Y/%m-%d_{price_area}.json"),
    )
    response = requests.get(url)
    return json.loads(response.content)


def analyze_prices(json_data, max_price):
    matches = list()
    for entry in json_data:
        if entry["NOK_per_kWh"] > max_price:
            return entry

    return None


def get_mailing_list():
    mailing_list_file = "mailing-list.txt"
    mail_data = []

    with open(mailing_list_file, encoding="utf-8") as mailing_list:
        for line in mailing_list:
            entry = line.split(",")
            if len(entry) != 2:
                raise IOError(f"{mailing_list_file} was malformed")

            email = entry[0]
            price_area = entry[1]

            mail_data.append({"email": email, "price_area": price_area})

    return mail_data


def send_mail(recipient, price_data):
    config = configparser.ConfigParser()
    config.read("credentials.conf")

    port = 465

    smtp_server = "smtp.gmail.com"
    sender = config["credentials"]["email"]
    password = config["credentials"]["password"]

    message = EmailMessage()
    peak_time = dateutil.parser.isoparse(price_data["time_start"])
    message.set_content(
        "Hei, jeg har laget et program som varsler når strømprisene er høye!\n"
        + peak_time.strftime("%d/%m/%Y %H:%M")
        + f" vil strømprisen være {price_data['NOK_per_kWh']} NOK per kWh"
    )
    message["Subject"] = "Strømprisvarsel"
    message["From"] = sender
    message["To"] = recipient

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender, password)
        server.send_message(message, from_addr=sender, to_addrs=recipient)


def main():
    for user in get_mailing_list():
        json_data = get_power_prices(user["price_area"])
        price_data = analyze_prices(json_data, 1.0)
        if price_data:
            send_mail(user["email"], price_data)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(ex)
        # with open("/var/log/stromvarsel.log", "a+", encoding="utf-8") as errlog:
        #     errlog.write("test")
