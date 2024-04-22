import configparser
import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import re
import requests
import smtplib
import ssl

import dateutil.parser
import jinja2
import urllib.parse


def get_power_prices(price_area):
    BASE_URL = "https://www.hvakosterstrommen.no/api/v1/prices/"

    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)

    url = urllib.parse.urljoin(
        BASE_URL,
        tomorrow.strftime(f"%Y/%m-%d_{price_area}.json"),
    )
    response = requests.get(url)
    return json.loads(response.content)


def analyze_prices(json_data, max_price):
    matches = list()
    for entry in json_data:
        if entry["NOK_per_kWh"] > max_price:
            matches.append(entry)

    return matches


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


def iso_time_to_time(timestring):
    return dateutil.parser.isoparse(timestring).strftime("%H:%M")


def iso_time_to_date(timestring):
    return dateutil.parser.isoparse(timestring).strftime("%d/%m/%Y")


def iso_time_to_date_time(timestring):
    return dateutil.parser.isoparse(timestring).strftime("%d/%m/%Y %H:%M")


def get_peak_time_text(peak_data):
    return (
        iso_time_to_date_time(peak_data["time_start"])
        + f" vil strømprisen være {peak_data['NOK_per_kWh']} NOK per kWh\n"
    )


def generate_chart_url(data):
    prices: list[str] = list()
    times: list[str] = list()
    for entry in data:
        prices.append(str(entry["NOK_per_kWh"]))
        times.append(iso_time_to_time(entry["time_start"]))

    with open("template.j2") as file:
        template = jinja2.Template(file.read())
        content = template.render(
            times=times,
            prices=prices,
            date=iso_time_to_date(data[0]["time_start"]),
        )

        url = "https://quickchart.io/chart?c=" + re.sub(
            " +",
            " ",
            json.dumps(
                json.loads(content.replace("\n", "")), separators=(",", ":")
            ),
        )
        return url


def create_email_body(price_data, img_url):
    message_content = list()

    message_content.append(
        MIMEText(
            "Hei,\n"
            "Dette er en automatisk varslingstjeneste for høye strømpriser!\n"
            "I morgen vil strømprisene overstige 1 NOK per kWH.\n\n",
            "plain",
        )
    )

    for entry in price_data:
        message_content.append(MIMEText(get_peak_time_text(entry), "plain"))

    # Create a related MIME multipart to embed the image
    related = MIMEMultipart("related")

    # Add the HTML content with the img tag referencing the image
    html_content = f"<p><img src='cid:image'></p>"
    message_content.append(MIMEText(html_content, "html"))

    # Fetch the image from the URL and attach it
    response = requests.get(img_url)
    img_data = response.content
    img = MIMEImage(img_data, "png")
    img.add_header("Content-ID", "<image>")
    related.attach(img)

    # Attach the related part to the main message
    message_content.append(related)

    message_content.append(MIMEText("\nMvh\nStrømprisvarsel", "plain"))

    return message_content


def send_mail(recipient, price_data, img_url):
    config = configparser.ConfigParser()
    config.read("credentials.conf")

    port = 465

    smtp_server = "smtp.gmail.com"
    sender = config["credentials"]["email"]
    password = config["credentials"]["password"]

    message = MIMEMultipart()

    message["Subject"] = "Strømprisvarsel"
    message["From"] = sender
    message["To"] = recipient

    message_parts = create_email_body(price_data, img_url)
    for part in message_parts:
        message.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender, password)
        server.send_message(message, from_addr=sender, to_addrs=recipient)


def main():
    for user in get_mailing_list():
        json_data = get_power_prices(user["price_area"])
        price_data = analyze_prices(json_data, 1.0)
        if price_data:
            send_mail(user["email"], price_data, generate_chart_url(json_data))


if __name__ == "__main__":
    main()
