import sys
import re
import time
from typing import Set
from typing_extensions import Final
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import datetime
import subprocess
import http.cookiejar

import browsercookie
import bs4
import fake_useragent
import mechanize

import getpass
from optparse import OptionParser


INITIAL_PAGE: Final = 'https://www.amazon.com/gp/vine/'
QUEUE_URL: Final = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_Default'
VFA_URL: Final = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_LastChance'
USER_AGENT: Final[str] = fake_useragent.UserAgent().ff


def create_browser() -> mechanize.Browser:
    browser = mechanize.Browser()
    firefox = getattr(browsercookie, OPTIONS.browser)()

    # Create a new cookie jar for Mechanize
    cj = http.cookiejar.CookieJar()
    for cookie in firefox.get_cookies():
        cj.set_cookie(cookie)
    browser.set_cookiejar(cj)

    # Necessary for Amazon.com
    browser.set_handle_robots(False)
    browser.addheaders = [('User-agent', USER_AGENT)]

    try:
        print('Connecting...')
        html = browser.open(INITIAL_PAGE).read()

        # Are we already logged in?
        if b'The Exclusive Club of Influential Amazon Voices.' in html:
            return browser

        print('Could not log in with a cookie')
        sys.exit(1)
    except urllib.error.HTTPError as e:
        print(e)
    except urllib.error.URLError as e:
        print('URL Error', e)

    sys.exit(1)


def download_vine_page(br, url, name=None):
    if name:
        print(f"\nChecking {name}...")
    try:
        response = br.open(url)
    except:
        return None

    if name:
        print('  Downloading...')

    html = response.read()

    if name:
        print('  Parsing...')

    return bs4.BeautifulSoup(html, features="lxml")


def get_list(br, url, name) -> Set[str]:
    soup = download_vine_page(br, url, name)
    if not soup:
        raise

    asins: Set[str] = set()

    for link in soup.find_all('tr', {'class': 'v_newsletter_item'}):
        if link['id'] in asins:
            print('Duplicate in-stock item:', link['id'])
        asins.add(link['id'])

    # Find list of out-of-stock items.  All of items listed in the
    # 'vineInitalJson' variable are out of stock.  Also, Amazon's web
    # developers don't know how to spell.  "Inital"?  Seriously?
    for script in soup.find_all('script', {'type': 'text/javascript'}):
        for s in script.findAll(text=True):
            m = re.search(r'^.*vineInitalJson(.*?)$', s, re.MULTILINE)
            if m:
                # {asin:"B007XPLI56"},
                oos = re.findall(
                    '{"asin":"([^"]*)"}', m.group(0))

                # Remove all out-of-stock items from our list
                asins.difference_update(oos)

    print('Found %u items' % len(asins))
    return asins


def open_product_page(br, link, url) -> bool:
    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), end=' ')
    soup = download_vine_page(br, url % link)
    # Make sure we don't get a 404 or some other error
    if soup:
        print('New item:', link)
        # Display how much tax it costs
        tags = soup.find_all('p', text=re.compile(
            'Estimated tax value : \$[0-9\.]*'))
        if tags:
            tag = tags[0].contents[0]
            m = re.search('\$([0-9\.]*)', tag)
            if m:
                cost = float(m.group(1))
                print('Tax cost: $%.2f' % cost)
        webbrowser.open_new_tab(url % link)
        time.sleep(1)
        return True
    else:
        print('Invalid item:', link)
        return False


parser = OptionParser(usage="usage: %prog [options]")
parser.add_option("-w", dest="wait",
                  help="Number of minutes to wait between iterations (default is %default minutes)",
                  type="int", default=10)
parser.add_option('--browser', dest='browser',
                  help='Which browser to use ("firefox" or "chrome") from which to load the session cookies (default is "%default")',
                  type="string", default='firefox')

(OPTIONS, _args) = parser.parse_args()

BROWSER: Final = create_browser()

your_queue_list = get_list(BROWSER, QUEUE_URL, "your queue")
vine_for_all_list = get_list(BROWSER, VFA_URL, "Vine for All")

if not vine_for_all_list:
    print('Cannot get VfA list')
    sys.exit(1)


while True:
    print("\nWaiting %u minute%s" %
          (OPTIONS.wait, 's'[OPTIONS.wait == 1:]) + "\n")
    time.sleep(OPTIONS.wait * 60)

    your_queue_list2 = get_list(BROWSER, QUEUE_URL, "Your Queue")
    if your_queue_list2:
        for link in your_queue_list2.copy():
            if link not in your_queue_list:
                if not open_product_page(BROWSER, link, 'https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_Default'):
                    # If the item can't be opened, it might be because the web site
                    # isn't ready to show it to me yet.  Remove it from our list so
                    # that it appears again as a new item, and we'll try again.
                    your_queue_list2.remove(link)

        # If there are no items, then assume that it's a glitch.  Otherwise, the
        # next pass will think that all items are new and will open a bunch of
        # browser windows.
        your_queue_list = your_queue_list2

    vine_for_all_list2 = get_list(BROWSER, VFA_URL, "Vine For All")
    if vine_for_all_list2:
        for link in vine_for_all_list2.copy():
            if link not in vine_for_all_list:
                if not open_product_page(BROWSER, link, 'https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_LastChance'):
                    # If the item can't be opened, it might be because the web site
                    # isn't ready to show it to me yet.  Remove it from our list so
                    # that it appears again as a new item, and we'll try again.
                    vine_for_all_list2.remove(link)

        # If there are no items, then assume that it's a glitch.  Otherwise, the
        # next pass will think that all items are new and will open a bunch of
        # browser windows.
        vine_for_all_list = vine_for_all_list2
