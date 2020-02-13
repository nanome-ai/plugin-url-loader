import re
import json
import os
from functools import partial
import requests

import nanome
from .Settings import Settings

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
MENU_PATH = os.path.join(BASE_PATH, 'json', 'menus', 'Auth.json')

class Authentication():
    def __init__(self, plugin, settings, session, on_close):
        self.__plugin = plugin
        self.__settings = settings
        self.session = session
        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.__menu.register_closed_callback(on_close)
        self.__plugin.menu.root.get_children().append(self.__menu.root)

        self.inp_username = self.__menu.root.find_node('Username Input').get_content()
        self.inp_password = self.__menu.root.find_node('Password Input').get_content()

        self.btn_authenticate = self.__menu.root.find_node('Authenticate').get_content()
        self.btn_authenticate.register_pressed_callback(self.authenticate)

    def open_menu(self):
        self.__menu.enabled = True
        self.__menu.index = 2
        self.__plugin.update_menu(self.__menu)

    def close_menu(self):
        self.__menu.enabled = False
        self.__plugin.update_menu(self.__menu)
        self.__plugin.open_menu()

    def authenticate(self, button):
        button.unusable = True
        self.__plugin.update_content(button)
        auth_url = self.__settings.authentication_url
        if auth_url:
            credentials = {'isid': self.inp_username.input_text, 'password': self.inp_password.input_text }
            # TODO: Fill this in after email followup
            # result = self.session.get(url = auth_ur, headers={'Authorization': })
            print(f'result: {result.text}')
            # if result.status_code == requests.codes.ok:
            if True:
                self.__plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Authenticated Successfully")
                self.close_menu()
            else:
                self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Could not Authenticate.")

            button.unusable = False
            self.__plugin.update_content(button)


    def get_cookie(self, name):
        cookies = self.session.cookies.get_dict()
        cookies[name] = '7AC07AC0'
        return cookies.get(name, None)