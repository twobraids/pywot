#!/usr/bin/env python3

"""This Web Thing implements Thing for the Things Gateway from Mozilla that can send SMS
messages via Twilio.

--help will give a complete listing of the options.
--admin.dump_conf=my_config.ini  will create an ini file that then can be edited to
    set the parameters.
--admin.conf=my_config.ini will thereafter load configuration from the file.
"""

import aiohttp
import async_timeout
import logging

from functools import partial
from twilio.rest import Client

from pywot import (
    WoTThing,
    logging_config,
    log_config
)
from configman import (
    configuration,
    Namespace,
    class_converter,
)


class TwilioSMS(WoTThing):
    required_config = Namespace()
    required_config.add_option(
        'twilio_account_sid',
        doc='the Twilio Account SID',
        default="NOT A REAL SID",
    )
    required_config.add_option(
        'twilio_auth_token',
        doc='the Twilio Auth Token',
        default="NOT A REAL AUTH TOKEN",
    )
    required_config.add_option(
        'from_number',
        doc="the user's Twilio phone number (+1XXXYYYZZZZ)",
        default="+1XXXYYYZZZZ",
    )

    def __init__(self, config):
        super(TwilioSMS, self).__init__(
            config,
            "Twilio SMS",
            "thing",
            "a gateway for sending SMS"
        )

    def set_to_number(self, to_number):
        self.send_twilio_sms(to_number, None)

    def set_message(self, message):
        self.send_twilio_sms(None, message)

    def send_twilio_sms(self, to_number, message):
#         logging.debug('args %s, kwargs: %s', args, kwargs)
        if to_number is not None:
            self.to_number = to_number
        if message is not None:
            self.message = message
        if self.to_number is None or self.message is None:
            logging.debug('NOT READY: to_number: %s, message: %s', self.to_number, self.message)
            return
        logging.debug('sending SMS')
        client = Client(self.config.twilio_account_sid, self.config.twilio_auth_token)
        message = client.messages.create(
            body=self.message,
            from_=self.config.from_number,
            to=self.to_number
        )
        self.to_number = None
        self.message = None

    to_number = WoTThing.wot_property(
        name='to_number',
        initial_value=None,
        type='string',
        description='the number to send to',
        value_forwarder=set_to_number
    )
    message = WoTThing.wot_property(
        name='message',
        initial_value=None,
        type='string',
        description='the body of the SMS message',
        value_forwarder=set_message
    )


if __name__ == '__main__':
    required_config = Namespace()
    required_config.server = Namespace()
    required_config.server.add_option(
        name='wot_server_class',
        default="pywot.WoTServer",
        doc="the fully qualified name of the WoT Server class",
        from_string_converter=class_converter
    )
    required_config.add_option(
        name="sms_class",
        default=TwilioSMS,
        doc="the fully qualified name of the class that can send SMS",
        from_string_converter=class_converter
    )
    required_config.update(logging_config)
    config = configuration(required_config)

    logging.basicConfig(
        level=config.logging_level,
        format=config.logging_format
    )
    log_config(config)

    twilio_sms_gateway = config.sms_class(config)

    server = config.server.wot_server_class(
        config,
        [twilio_sms_gateway],
        port=config.server.service_port
    )
    server.run()
    logging.debug('done.')
