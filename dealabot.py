#!/bin/env python3

import sys
import time
import requests
from lxml import html

HOME_PAGE_URL = "https://www.dealabs.com/new.html"
FETCH_DELAY = 60
PAGES_TO_FETCH = 5

DEAL_NAME = 0
DEAL_URL = 1
DEAL_PRICE = 2
DEAL_SCORE = 3

def remove_prefix(s, prefix):
    return s if not s.startswith(prefix) else s[len(prefix):]

def remove_suffix(s, suffix):
    if len(suffix) == 0:
        return s

    return s if not s.endswith(suffix) else s[:-len(suffix)]

def get_deals_by_page(page_num):
    """Returns the list of deals from the given page number. The list of deals is
    composed of tuples. Use DEAL_URL, DEAL_NAME, DEAL_PRICE and DEAL_SCORE to
    retrieve position of the data."""
    r = requests.get(HOME_PAGE_URL, params={'page':str(page_num)})
    if r.status_code != 200:
        # Other errors will raise exceptions so we don't really care about them.
        # We probably should however.
        return []

    root = html.fromstring(r.text)
    article_nodes = root.xpath('//article[contains(@class, "deal_index_article")]')
    
    deals = []
    for article_node in article_nodes:
        title_node = article_node.xpath('.//a[@class="title"]')[0]
        price_node = article_node.xpath('.//span[contains(@class,"deal_price")]')
        score_node = article_node.xpath('.//div[contains(@class, "temperature_div")]/p')
        
        price = None if len(price_node) == 0 else price_node[0].text
        score = None if len(score_node) == 0 else score_node[0].text
        if score == "new":
            score = 0
        elif score != None:
            score = int(remove_suffix(remove_prefix(score, "\xa0"), '°'))

        deals.append((
            title_node.text, # DEAL_NAME
            title_node.get('href'), # DEAL_URL
            price, # DEAL_PRICE
            score, # DEAL_SCORE
        ))

    return deals

def get_deals(num_pages):
    """Returns the list of deals from page 1 to num_pages. See get_deals_by_page()
    for details on how the data is stored."""
    return list(map(get_deals_by_page, range(1, num_pages+1)))

def notifier_freemobile(msg, params):
    """Sends a SMS with the Free Mobile API. Returns True on success."""
    params = params.split(",")
    params = {
            "user": params[0],
            "pass": params[1],
            "msg": msg,
    }
    r = requests.get("https://smsapi.free-mobile.fr/sendmsg", params=params)
    print("notifier_freemobile: {} {}".format(params, r.status_code))
    return r.status_code == 200

def notifier_stdout(msg, params):
    """Prints message with stdout. Always returns True."""
    print(msg)
    return True

notifiers = {
        'freemobile': notifier_freemobile,
        'stdout': notifier_stdout,
        '-': notifier_stdout,
}

def main(args):
    if len(args) < 4:
        print("Usage: {} <notifier> <notifier parameters> <keywords...>".format(args[0]))
        sys.exit(1)

    notifier = notifiers[args[1]]
    notifier_params = args[2]

    keywords = set(map(str.lower, args[3:]))

    notified_urls = set()
    
    def is_keyword_in_string(s, keywords):
        for keyword in keywords:
            if keyword in s:
                return True
        return False

    while True:
        deals = get_deals(PAGES_TO_FETCH)
        print("Got {} deals".format(len(deals)))
        for deal in deals:
            # We only want to send a notification once for every deal.
            # No need to spam.
            if is_keyword_in_string(deal[DEAL_NAME].lower(), keywords) and \
                not deal[DEAL_URL] in notified_urls:
                    notifier("Get your credit card ready! {} ({}) {}".format(
                        deal[DEAL_NAME],
                        deal[DEAL_SCORE],
                        deal[DEAL_URL],
                    ), notifier_params)
                    notified_urls.add(deal[DEAL_URL])

        time.sleep(FETCH_DELAY)

if __name__ == '__main__':
    main(sys.argv)
