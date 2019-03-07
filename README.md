Viner
=====

This program is a Python script that checks the list of products on your
Amazon Vine queue and notifies you if a new item becomes available.

If you don't know what Amazon Vine is, please read the [Wikipedia page](http://en.wikipedia.org/wiki/Amazon_Vine).

Amazon Vine is an invitation-only program, and there nothing you can do
to get an invitation, not even from other Vine members.  I have no idea
why I was invited.

IMPORTANT: Log in via a web browser first
-----------------------------------------

This script can not log into Amazon.com by itself.  It needs the
help of your web browser.  Specifically, it uses the 'browsercookie'
package to copy the session cookies from your web browser during the
login process.  See the [browsercookie web page](https://pypi.python.org/pypi/browsercookie/)
for a list of browsers that are supported.

Here are the steps:

    1) Load the browser
    2) Make sure cookies are fully enabled.
    3) Log into Amazon.
    4) Quit the browser (this will ensure the cookies are saved to disk)
    5) Launch the script.  Specify the --browser option if you used Chrome

The script will then load the cookies from your browser's cookie file,
and then use those cookies to log into Amazon.com.

Credits
-------
Original Python 2 version: [@timur-tabi](https://github.com/timur-tabi)
