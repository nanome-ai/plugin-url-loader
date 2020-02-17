import os
import re
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement
from . import ResponseConfigurationMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "ResourceConfig.json")

class ResourceConfigurationMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.response_config = ResponseConfigurationMenu(plugin, settings)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 4

        self.resource = None
        self.step_elements = []

        self.headers_i = 1

        self.inp_resource_url = self.menu.root.find_node('URL Input').get_content()
        self.inp_resource_url.register_changed_callback(self.resource_url_changed)
        self.ls_request_types = self.menu.root.find_node('Request Types').get_content()
        self.pfb_header = self.menu.root.find_node('Header Prefab')
        self.ls_headers = self.menu.root.find_node('Headers List').get_content()
        self.btn_response_config = self.menu.root.find_node('Configure Button').get_content()
        self.btn_response_config.register_pressed_callback(self.open_response_config)
        self.inp_import_name = self.menu.root.find_node('Import Name Input').get_content()
        self.inp_import_name.register_changed_callback(self.import_name_changed)
        self.ls_import_types = self.menu.root.find_node('Import Type List').get_content()
        self.inp_post_data = self.menu.root.find_node('Data Input').get_content()
        self.inp_post_data.register_changed_callback(self.data_changed)
        self.prepare_menu()

    def open_menu(self, resource):
        self.menu.enabled = True
        self.set_resource(resource)
        self.plugin.update_menu(self.menu)

    def open_response_config(self, button):
        self.response_config.open_menu(self.resource)

    def prepare_menu(self):
        for method in ['get', 'post']:
            ln = nanome.ui.LayoutNode()
            ln.name = method
            btn = ln.add_new_button(method)
            btn.register_pressed_callback(self.set_resource_method)
            self.ls_request_types.items.append(ln)

        for import_type in ['.pdb', '.cif', '.sdf', '.pdf', '.nanome', '.json']:
            ln = nanome.ui.LayoutNode()
            ln.name = import_type
            btn = ln.add_new_button(import_type)
            btn.register_pressed_callback(self.set_resource_import_type)
            self.ls_import_types.items.append(ln)

    def set_resource(self, resource):
        self.resource = resource
        self.inp_resource_url.input_text = resource['url']
        self.update_request_type()
        self.set_headers(resource['headers'])
        self.update_import_type()
        self.inp_post_data.input_text = resource['data']
        self.inp_post_data.register_changed_callback(self.set_resource_default_data)

    def import_name_changed(self, text_input):
        new_name = re.sub('([^0-9A-z-._~])', '', text_input.input_text)
        self.settings.change_resource(self.resource, new_import_name=new_name)

    def resource_url_changed(self, text_input):
        self.settings.change_resource(self.resource, new_url=text_input.input_text)
        if self.plugin.make_request.request:
            if self.resource['references'].get(self.plugin.make_request.request['name']):
                self.plugin.make_request.show_request()

    def data_changed(self, text_input):
        self.settings.change_resource(self.resource, new_data=text_input.input_text)

    def add_step_dependency(self, step_element, reset=False):
        if reset:
            self.steps = []
        self.step_elements.append(step_element)

    def update_request_type(self):
        for ln_method in self.ls_request_types.items:
            btn = ln_method.get_content()
            btn.selected = ln_method.name == self.resource['method']
        self.plugin.update_content(self.ls_request_types)

    def update_import_type(self):
        for ln_import_type in self.ls_import_types.items:
            btn = ln_import_type.get_content()
            btn.selected = ln_import_type.name == self.resource['import type']
        self.plugin.update_content(self.ls_import_types)

    def set_headers(self, headers):
        self.ls_headers.items = []
        for i, (name, value) in enumerate(headers.items()):
            pfb = self.header_prefab(i, name, value)
            self.ls_headers.items.append(pfb)
        ln_new_header = nanome.ui.LayoutNode()
        btn = ln_new_header.add_new_button('New Header')
        btn.register_pressed_callback(self.new_header)
        self.ls_headers.items.append(ln_new_header)

    def header_prefab(self, i, name, value):
        pfb = self.pfb_header.clone()
        ln_delete = pfb.find_node('Delete')
        ln_delete.get_content().element = pfb
        name_input = pfb.find_node('Name').get_content()
        value_input = pfb.find_node('Value').get_content()
        name_input.input_text = name
        value_input.input_text = value
        name_input.register_changed_callback(partial(self.set_header, i, name_input, value_input))
        value_input.register_changed_callback(partial(self.set_header, i, name_input, value_input))
        ln_delete.get_content().register_pressed_callback(self.delete_header)
        return pfb

    def new_header(self, button):
        header_name = f"Header {self.headers_i}"
        self.headers_i += 1
        self.resource['headers'][header_name] = ''
        pfb = self.header_prefab(header_name, '')
        self.ls_headers.items.insert(len(self.ls_headers.items)-1, pfb)
        self.plugin.update_content(self.ls_headers)

    def delete_header(self, button):
        header_name = button.element.find_node('Name').get_content().input_text
        self.resource['headers'].pop(header_name)
        self.ls_headers.items.remove(button.element)
        self.plugin.update_content(self.ls_headers)

    def set_header(self, i, name_input, value_input, text_input):
        if name_input.input_text and value_input.input_text:
            self.settings.set_header(i, name_input.input_text, value_input.input_text)

    def set_resource_method(self, button=None):
        if self.resource:
            self.resource['method'] = button.text.value.idle
            self.update_request_type()
            self.plugin.update_content(button)
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource undefined")

    def set_resource_import_type(self, button=None):
        if self.resource:
            self.resource['import type'] = button.text.value.idle if not button.selected else None
            self.update_import_type()
            self.plugin.update_content(button)
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource undefined")

    def set_resource_default_data(self, text_input=None):
        self.resource['data'] = text_input.input_text