#! /usr/bin/python
# -*- coding: UTF-8 -*- vim: et ts=4 sw=4
"""
Cloud Cruiser Report Emailer

This script takes in arguments from the 
command line to generate and email Cloud Cruiser reports
from the API.

Example usage:
python ccreportemailer.py --url http://cloudcruiser.mysite.com:8080 --username rcurrah --password mypass --usergroup-name admin --report-name MyReport --email-server smtp.mysite.com --email-from ryan@mysite.com --email-to ryan@mysite.com,david@mysite.com --debug true
"""
import requests
import StringIO
import csv
import logging
import smtplib
import argparse
from email.mime.text import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders
from datetime import datetime
from lxml import etree


url = ''  # no trailing forward slash (/)
username = ''
password = ''
usergroup_name = ''
report_name = ''
date_range = ''
csv_name = ''
csv_headers = ''
email_server = ''
email_from = ''
email_to = ''
file_format = 'CSV'

API_URI = '/rest/v2/reports'  # must start with forward slash (/)
XML_SCHEMA = 'http://www.cloudcruiser.com/webservices/v2/Report'


def main():
    global url
    global username
    global password
    global usergroup_name
    global report_name
    global date_range
    global csv_name
    global csv_headers
    global email_server
    global email_from
    global email_to
    global email_tls

    parser = argparse.ArgumentParser(description='Generate a Cloud Cruiser report and send to email.')
    parser.add_argument('--url', type=str, required=True,
                        help='cloud cruiser url... example: http://cloudcruiser.mysite.com:8080')
    parser.add_argument('--username', type=str, required=True, help='Cloud Cruiser username')
    parser.add_argument('--password', type=str, required=True, help='Cloud Cruiser password')
    parser.add_argument('--usergroup-name', type=str, required=True,
                        help='The group whose permissions control the data that the report retrieves')
    parser.add_argument('--report-name', type=str, required=True, help='The name of the report to run')
    parser.add_argument('--date-range', type=str, default='PREVMON',
                        choices=['ALL', 'CURRPERIOD', 'PREVPERIOD', 'CURRMON', 'MONTHTODATE',
                                 'PREVMON', 'CURRYEAR', 'YEARTODATE', 'PREVYEAR', 'TODAY', 
                                 'PREVTODAY', 'CURRWEEK', 'WEEKTODATE', 'PREVWEEK'],
                        help='The date range for which to retrieve data. Used for reports ' \
                             'whose time frame is a date range.')
    parser.add_argument('--csv-name', type=str, help='Csv file name')
    parser.add_argument('--csv-headers', type=str, help='Overide the default csv headers')
    parser.add_argument('--email-server', type=str, required=True, help='Email smtp server address')
    parser.add_argument('--email-tls', choices=['true'], help='Email tls enabled')
    parser.add_argument('--email-from', type=str, required=True, help='Email from address')
    parser.add_argument('--email-to', type=str, required=True,
                        help='Email to address... multiple addresses can be added separated by a comma')
    parser.add_argument('--debug', choices=['true'], help='Print debug statements')

    args = parser.parse_args()

    logging_format = '%(asctime)s %(levelname)s: %(message)s'
    if args.debug:
        logging.basicConfig(format=logging_format, level=logging.DEBUG)
    else:
        logging.basicConfig(format=logging_format, level=logging.INFO)

    url = args.url
    username = args.username
    password = args.password
    usergroup_name = args.usergroup_name
    report_name = args.report_name
    date_range = args.date_range
    csv_name = args.csv_name if args.csv_name and \
               args.csv_name.endswith('.csv') else \
               "{0}.csv".format(args.csv_name) if \
               args.csv_name else \
               "{0}.csv".format(report_name)
    csv_headers = args.csv_headers
    email_server = args.email_server
    email_tls = args.email_tls
    email_from = args.email_from
    email_to = args.email_to

    report = get_report()
    report = format_csv(report)
    email_report(report)
    return

def get_report():
    """
    Query Cloud Cruiser API and download report
    Returns a csv reader object (could change to support more filetypes)
    """
    logging.info('Retrieving report from Cloud Cruiser API.')
    # Build up XML data
    root = etree.Element("reportInput", nsmap={None: XML_SCHEMA})
    etree.SubElement(root, "reportName").text = report_name
    etree.SubElement(root, "userGroupName").text = usergroup_name
    etree.SubElement(root, "format").text = file_format
    etree.SubElement(root, "dateRange").text = date_range
    # Send post request
    headers = {'Content-Type': 'application/xml'}
    r = requests.post('{url}{API_URI}'.format(url=url.rstrip('/'),
                                              API_URI=API_URI if API_URI.startswith('/') else ('/' + API_URI)),
                      headers=headers,
                      auth=(username, password),
                      data=etree.tostring(root))
    report = csv.reader(r.text.splitlines(), delimiter=',')
    logging.info('Retrieved report from Cloud Cruiser API.')
    return report

def format_csv(report):
    """
    Format the csv file, overwrite the header if required
    Returns a csv writer object
    """
    logging.info('Formatting CSV report.')
    csv_file = StringIO.StringIO()
    writer = csv.writer(csv_file)
    for i, row in enumerate(report):
        logging.debug("{0} {1}".format(type(row), row))
        # Save the first header
        if i == 0:
            orig_header = row
        # Overwrite header if new one inputted
        if i == 0 and csv_headers:
            writer.writerow(csv_headers.split(','))
            continue
        # Bug fix - Cloud Cruiser reports API uses pagination
        # Which results in a lot of headers repeating in the doc
        # This fix matches on the row against the header if they
        # match it will skip adding to the report.
        if not i == 0 and not cmp(orig_header, row):
            continue
        writer.writerow(row)
    logging.info('Finished formatting CSV report.')
    return csv_file

def email_report(report):
    """
    Takes in a csv writer object and sends as an email attachment
    """
    html = '<html>' \
           '<body>' \
           '<b>Report name:</b> {report_name}<br />' \
           '<b>Generated on:</b> {date}<br />' \
           '<b>Date range:</b> {date_range}<br />' \
           '</body>' \
           '</html>'.format(report_name=report_name,
                            date=datetime.now(),
                            date_range=date_range)

    # Create email
    msg = MIMEMultipart()
    msg['Subject'] = 'Generated {report_name} on {date}'.format(report_name=report_name, date=datetime.now())
    msg['From'] = email_from
    msg['To'] = email_to

    # Attach body
    body = MIMEText(html, 'html')
    msg.attach(body)

    # Attach file
    file_attach = MIMEBase('application', "octet-stream")
    file_attach.set_payload(report.getvalue())
    Encoders.encode_base64(file_attach)
    file_attach.add_header('Content-Disposition', 'attachment; filename="{csv_name}"'.format(csv_name=csv_name))
    msg.attach(file_attach)

    # Send email
    if email_tls:
        server = smtplib.SMTP_SSL(email_server)
    else:
        server = smtplib.SMTP(email_server)
    server.sendmail(email_from, email_to, msg.as_string())
    logging.info('Report email sent.')
    return


if __name__ == "__main__":
    main()
