# python-ccreportemailer

Easily email Cloud Cruiser reports with this Python tool. You can use this in
combination with a scheduler like cron to email the reports automatically.


# requires

- requests: https://pypi.python.org/pypi/requests
- lxml: https://pypi.python.org/pypi/lxml
- argparse: https://pypi.python.org/pypi/argparse


# usage instructions

```bash
ryan@ryan$ ccreportemailer.py --url http://cloudcruiser.mysite.com:8080 --username rcurrah --password mypass --usergroup-name admin --report-name MyReport --email-server smtp.mysite.com --email-from ryan@mysite.com --email-to ryan@mysite.com,david@mysite.com --debug true
```