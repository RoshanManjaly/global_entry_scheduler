import os, json
import requests
import hashlib
import logging
from datetime import datetime
from twilio.rest import Client

GOES_URL_FORMAT = 'https://ttp.cbp.dhs.gov/schedulerapi/slots?orderBy=soonest&limit=3&locationId={0}&minimum=1'

def notify_sms(settings, dates, location_name):
    try:
        account_sid = settings['twilio_account_sid']
        auth_token = settings['twilio_auth_token']
        from_number = settings['twilio_from_number']
        to_number = settings['twilio_to_number']

        client = Client(account_sid, auth_token)
        for avail_apt in dates:
            body = 'New Global Entry appointment available at %s on %s' % (location_name, avail_apt)
            message = client.messages.create(body=body, to=to_number, from_=from_number)
            logging.info(f'SMS sent: {message.sid}')
    except Exception as e:
        logging.error(f'Failed to send SMS: {e}')

def check_appointments(settings):
    try:
        response = requests.get(GOES_URL_FORMAT.format(settings['enrollment_location_id']))
        data = response.json()

        if not data:
            logging.info('No appointments available.')
            return

        current_apt = datetime.strptime(settings['current_interview_date_str'], '%Y-%m-%d')
        dates = []
        for slot in data:
            if slot['active']:
                appointment_date = datetime.strptime(slot['startTimestamp'], '%Y-%m-%dT%H:%M')
                if current_apt > appointment_date:
                    dates.append(appointment_date.strftime('%A, %B %d @ %I:%M%p'))

        if dates:
            location_name = settings.get("enrollment_location_name", settings['enrollment_location_id'])
            notify_sms(settings, dates, location_name)
        else:
            logging.info('No new appointments found that are earlier than the current one.')

    except Exception as e:
        logging.error(f'Error checking appointments: {e}')

def lambda_handler(event, context):
    # Assume 'settings' is passed in through the event or environment variables
    # For environment variables, use os.environ['VARIABLE_NAME']
    settings = {
        'twilio_account_sid': os.environ['TWILIO_ACCOUNT_SID'],
        'twilio_auth_token': os.environ['TWILIO_AUTH_TOKEN'],
        'twilio_from_number': os.environ['TWILIO_FROM_NUMBER'],
        'twilio_to_number': os.environ['TWILIO_TO_NUMBER'],
        'enrollment_location_id': os.environ['ENROLLMENT_LOCATION_ID'],
        'current_interview_date_str': os.environ['CURRENT_INTERVIEW_DATE_STR'],
        # Optionally, add 'enrollment_location_name' if you have a friendly name for the location
    }

    check_appointments(settings)

    return {
        'statusCode': 200,
        'body': json.dumps('Check and notification process completed.')
    }
