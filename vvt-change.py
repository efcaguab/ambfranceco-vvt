import datetime
import logging
import os
import requests
import smtplib
import ssl

from dotenv import load_dotenv
from retry import retry


URL = "https://co.ambafrance.org/VVT"
HISTORY_PATH = "vvt_history"
SERVER_ADDRESS = "smtppro.zoho.com"
SERVER_PORT = 465

logger = logging.getLogger(__name__)


@retry(tries=10, delay=30, backoff=2, logger=logger)
def get_page(url):
    request = requests.get(url)
    if request.status_code == 429:
        raise Exception("VVT complained with too many requests")
    return request.text


def save_page(page, filename):
    with open(filename, "w") as f:
        f.write(page)


def open_page(filename):
    with open(filename, "r") as f:
        return f.read()


def are_files_same(path1, path2):
    with open(path1, "r") as f1:
        with open(path2, "r") as f2:
            return f1.read() == f2.read()


def get_latest_page(path):
    pages = os.listdir(path)
    if len(pages) == 0:
        return None
    pages.sort()
    return pages[-1]


def send_email():
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SERVER_ADDRESS, SERVER_PORT, context=context) as server:
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        server.sendmail(
            from_addr=os.environ["SMTP_USER"],
            to_addrs=os.environ["SMTP_USER"],
            msg="Subject: VVT changed\n\nVVT changed",
        )


def main():
    load_dotenv()
    logger.info("Getting page...")
    page = get_page(URL)
    new_page = os.path.join(HISTORY_PATH, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ".html")
    logger.info("Saving page as %s", new_page)
    save_page(page, new_page)
    
    if not os.path.exists(HISTORY_PATH):
        os.mkdir(HISTORY_PATH)
    logger.info("Getting latest page saved...")
    latest_page = get_latest_page(HISTORY_PATH)

    delete_new_page = True
    if latest_page is None:
        logger.info("No old page to compare saved yet.")
        delete_new_page = False
    else:
        old_page = os.path.join(HISTORY_PATH, latest_page)
        logger.info("Latest page saved: %s", old_page)
        logger.info("Comparing pages...")
        if not are_files_same(new_page, old_page):
            logger.info("Pages are different.")
            delete_new_page = False
        else:
            logger.info("Pages are the same.")

    if delete_new_page:
        logger.info("Deleting new page.")
        os.remove(new_page)
    else:
        logger.info("Sending email.")
        send_email()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
