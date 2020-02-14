import os
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement
from . import RequestConfigurationMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "Requests.json")

class RequestsMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 1
        self.request_config = RequestConfigurationMenu(self.plugin, self.settings)

        self.req_i = 0

        self.requests_list = self.menu.root.find_node("Requests").get_content()
        self.btn_new_request = self.menu.root.find_node("New Request").get_content()
        self.btn_new_request.register_pressed_callback(self.add_request)

    def open_menu(self):
        self.refresh_requests()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)

    def add_request(self, button):
        name = f'Request {self.req_i}'
        self.settings.add_request(name)
        request =  self.settings.requests[name]
        self.req_i += 1
        element = ListElement(
            self.plugin,
            self.requests_list,
            name,
            externally_used=True,
            config=self.request_config,
            deleted=self.delete_request,
            renamed=partial(self.request_renamed, request),
            external_toggle=self.set_active_request,
            config_opened=partial(self.request_config.open_menu, request)
        )
        element.set_tooltip("Set to active request")
        self.requests_list.items.append(element)
        self.plugin.update_content(self.requests_list)

    def delete_request(self, element):
        return self.settings.delete_request(element.name)

    def request_renamed(self, request, element, new_name):
        return self.settings.rename_request(request, new_name)

    def set_active_request(self, list_element, toggled):
        for item in self.requests_list.items:
                item.set_use_externally(item is list_element and not toggled, update=False)
        self.plugin.request = self.settings.requests[list_element.name] if toggled else None
        self.plugin.show_request()
        return True

    def refresh_requests(self):
        self.requests_list.items = []
        for name, request in self.settings.requests.items():
            element = ListElement(
            self.plugin,
            self.requests_list,
            name,
            externally_used=True,
            config=self.request_config,
            deleted=self.delete_request,
            renamed=partial(self.request_renamed, request),
            external_toggle=self.set_active_request,
            config_opened=partial(self.request_config.open_menu, request)
            )
            element.set_tooltip("Set to active request")
            if self.plugin.request is request:
                element.set_use_externally(True)
            self.requests_list.items.append(element)