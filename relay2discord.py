import znc
import os
import requests
import string
import time
import re

from datetime import datetime
from random import randint as random_integer

IRC_PATTERN = r'[\x02\x0F\x16\x1D\x1F]|\x03(\d{,2}(,\d{,2})?)?'
NCDOT_FORMAT = re.compile(r'(BROADCAST)/(.*?)] (.*?): ', re.I)


class DiscordPinger(object):

    BASE          = 'https://discordapp.com'
    API_BASE      = BASE     + '/api/v6'
    LOGIN         = API_BASE + '/auth/login'
    LOGOUT        = API_BASE + '/auth/logout'
    CHANNELS      = API_BASE + '/channels'

    def __init__(self):
        self.headers = {}

    def login(self, email, password):
        payload = {'email': email, 'password': password}
        res = requests.post(self.LOGIN, json=payload)
        if res.status_code != 200:
            raise Exception('Invalid Login')

        jresp = res.json()

        self.headers['Authorization'] = jresp['token']

    def send_message(self, channel_id, message):
        url = '{0.CHANNELS}/{1}/messages'.format(self, channel_id)
        payload = {
            'content': str(message),
            'nonce': random_integer(-2**63, 2**63 - 1),
            'mention_everyone': True
        }
        res = requests.post(url, json=payload, headers=self.headers)
        if res.status_code != 200:
            raise Exception('Failed to send_message!')


class relay2discord(znc.Module):
    description = "Relay FleetBot ping's to Discord"
    module_types = [znc.CModInfo.NetworkModule,]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.discord = DiscordPinger()
        self.discord.login('username', 'password')

        self.global_ping_id = '151628748670631936'
        self.titan_ping_id = '153316816251387904'
        self.super_ping_id = '153316816251387904'
        self.corp_name = 'HIGH_FLYERS'

        self.alert_from = ('FleetBot', )
        self.last_msg_sent = ''
        self.last_msg_sent_t = 0
        # If the same message is repeated within this timeframe, ignore.
        self.repeat_spam_threshold = 2

    def OnPrivMsg(self, nick, zmessage):
        from_user = nick.GetNick()

        if from_user not in self.alert_from:
            return znc.CONTINUE

        message = re.sub(IRC_PATTERN, '', zmessage.s)
        notify_msg = '@everyone {} {:s}'.format(datetime.utcnow().strftime('%d/%m/%y %H:%M'), message)
        current_time = time.time()

        # Vince is probably spamming...
        if (message == self.last_msg_sent) and ((current_time - self.last_msg_sent_t) < self.repeat_spam_threshold):
            return znc.CONTINUE
        
        self.last_msg_sent = message
        self.last_msg_sent_t = time.time()

        # Titan ONLY pings
        if 'TITANS' in message and 'SUPERCARRIERS' not in message:
            self.discord.send_message(self.titan_ping_id, notify_msg)

        # Super ONLY Pings
        if 'SUPERCARRIERS' in message and 'TITANS' not in message:
            self.discord.send_message(self.super_ping_id, notify_msg)

        # Super & Titan Group Pings
        if 'SUPERCARRIERS' in message and 'TITANS' in message:
            # only send one ping if they are the same channels
            if self.super_ping_id == self.titan_ping_id:
                self.discord.send_message(self.super_ping_id, notify_msg)
            else:
                self.discord.send_message(self.titan_ping_id, notify_msg)
                self.discord.send_message(self.super_ping_id, notify_msg)

        # Global Ping's
        if 'NORTHERN_COALITION' in message or self.corp_name in message:
            self.discord.send_message(self.global_ping_id, notify_msg)

        return znc.CONTINUE