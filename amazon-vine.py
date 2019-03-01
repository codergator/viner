# Copyright 2014, Timur Tabi
# Copyright 2019, The Codergator
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import re
import time
from typing import Set
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


def user_agent() -> str:
    return fake_useragent.UserAgent().ff


QUEUE_URL = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_Default'
VFA_URL = 'https://www.amazon.com/gp/vine/newsletter?ie=UTF8&tab=US_LastChance'


def create_browser(user_agent) -> mechanize.Browser:
    global options

    br = mechanize.Browser()

    # Load cookies from the selected web browser
    cj2 = getattr(browsercookie, options.browser)()

    # Create a new cookie jar for Mechanize
    cj = http.cookiejar.CookieJar()
    for cookie in cj2.get_cookies():
        cj.set_cookie(cookie)

    # Load those cookies into mechanize for the session
    br.set_cookiejar(cj)

    # Necessary for Amazon.com
    br.set_handle_robots(False)
    br.addheaders = [('User-agent', user_agent)]

    try:
        print('Connecting to vine.amazon.com...')
        response = br.open('https://www.amazon.com/gp/vine/')
        html = response.read()

        # Are we already logged in?
        if b'The Exclusive Club of Influential Amazon Voices.' in html:
            return br
        else:
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
    global options

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


def open_vine_page(br, link, url) -> bool:
    global options

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

(options, args) = parser.parse_args()


USER_AGENT = user_agent()
BROWSER = create_browser(USER_AGENT)

your_queue_list = get_list(BROWSER, QUEUE_URL, "your queue")
vine_for_all_list = get_list(BROWSER, VFA_URL, "Vine for All")

if not vine_for_all_list:
    print('Cannot get VfA list')
    sys.exit(1)


while True:
    print("\nWaiting %u minute%s" %
          (options.wait, 's'[options.wait == 1:]) + "\n")
    time.sleep(options.wait * 60)

    your_queue_list2 = get_list(BROWSER, QUEUE_URL, "Your Queue")
    if your_queue_list2:
        for link in your_queue_list2.copy():
            if link not in your_queue_list:
                if not open_vine_page(BROWSER, link, 'https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_Default'):
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
                if not open_vine_page(BROWSER, link, 'https://www.amazon.com/gp/vine/product?ie=UTF8&asin=%s&tab=US_LastChance'):
                    # If the item can't be opened, it might be because the web site
                    # isn't ready to show it to me yet.  Remove it from our list so
                    # that it appears again as a new item, and we'll try again.
                    vine_for_all_list2.remove(link)

        # If there are no items, then assume that it's a glitch.  Otherwise, the
        # next pass will think that all items are new and will open a bunch of
        # browser windows.
        vine_for_all_list = vine_for_all_list2
