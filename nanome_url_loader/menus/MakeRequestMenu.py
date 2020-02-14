import re
import os
import requests
from functools import partial

import json
import requests
import tempfile
import traceback

import nanome
from nanome.util import Logs

from ..Settings import Settings
from .ResourcesMenu import ResourcesMenu
from .RequestsMenu import RequestsMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), 'json', 'MakeRequest.json')
class MakeRequestMenu(nanome.PluginInstance):
    def __init__(self):
        self.session = requests.Session()
        self.settings = Settings(self)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 0
        self.__requests = RequestsMenu(self, self.settings)
        self.__resources = ResourcesMenu(self, self.settings)
        self.__field_names = set()
        self.__field_values = {}

        self.request = None

        self.__ln_fields = self.menu.root.find_node('Fields')
        self.btn_all_requests = self.menu.root.find_node('All Requests').get_content()
        self.btn_all_requests.register_pressed_callback(lambda b: self.__requests.open_menu())
        self.btn_load = self.menu.root.find_node('Load Button').get_content()
        self.btn_load.register_pressed_callback(self.load_request)

    def start(self):
        self.set_plugin_list_button(self.PluginListButtonType.run, 'Save')
        self.set_plugin_list_button(self.PluginListButtonType.advanced_settings, 'Edit Resources')
        if self.settings.request_names:
            self.request = self.settings.requests[self.settings.request_names[0]]
            self.show_request()
        self.open_menu()

    def on_run(self):
        self.open_menu()
        self.settings.save_settings()

    def on_stop(self):
        self.settings.save_settings()

    def open_menu(self):
        self.menu.enabled = True
        self.update_menu(self.menu)

    def on_advanced_settings(self):
        self.__resources.open_menu()

    def show_request(self):
        self.__ln_fields.clear_children()
        if not self.request:
            self.update_menu(self.menu)
            return

        self.__field_names = self.settings.request_fields(self.request)
        self.__field_values = {name:'' for name in self.__field_names}
        for field_name in self.__field_names:
            field_value = self.__field_values.get(field_name, '')
            ln = nanome.ui.LayoutNode()
            ln.sizing_type = nanome.util.enums.SizingTypes.ratio
            ln.sizing_value = 0.25
            ln.layout_orientation = nanome.util.enums.LayoutTypes.horizontal
            ln.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)

            ln_label = ln.create_child_node()
            label = ln_label.add_new_label(field_name+':')
            label.text_max_size = 0.4
            label.text_vertical_align = nanome.util.enums.VertAlignOptions.Middle

            ln_field = ln.create_child_node()
            ln_field.forward_dist = 0.02
            ln_field.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)
            text_input = ln_field.add_new_text_input()
            text_input.input_text = field_value
            text_input.placeholder_text = ''
            text_input.max_length = 64
            text_input.register_changed_callback(partial(self.field_changed, field_name))
            text_input.register_submitted_callback(partial(self.clean_field, field_name, True))
            self.__ln_fields.add_child(ln)
        self.__ln_fields.create_child_node()
        self.update_menu(self.menu)

    def field_changed(self, field_name, text_input):
        self.__field_values[field_name] = text_input.input_text

    def clean_field(self, name, update=False, text_input=None):
        value = text_input.input_text if text_input else self.__field_values[name]
        self.__field_values[name] = re.sub('([^0-9A-z-._~{}$])', '', value)
        self.update_node(self.__ln_fields)

    def set_load_enabled(self, enabled):
        self.btn_load.unusable = not enabled
        self.update_content(self.btn_load)

    def load_request(self, button=None):
        if not self.request:
            self.send_notification(nanome.util.enums.NotificationTypes.message, "Please select a request")
            return

        for name in self.__field_names:
            self.clean_field(name)

        self.set_load_enabled(False)

        results = {}
        print(f'request: {self.request}')
        for step in self.request['steps']:
            resource = step['resource']
            variables, load_url = resource['variables'], resource['url']
            method, import_type = resource['method'].lower(), resource['import type']
            headers, data = resource['headers'], resource['data']

            # prepare the url
            last_var = None
            for var in variables:
                load_url = load_url.replace("{"+var+"}", self.__field_values[var])
                last_var = var

            # override data if necessary
            data_override_field_name = f"{self.request['name']} {step['name']} data"
            if step['override_data']:
                data = self.__field_values[data_override_field_name]
                print(f'overrode data to {data}')

            # construct headers and data from fields and step results
            if method == 'post':
                print(f'data before: {data}')
            for name, value in self.__field_values.items():
                old_data = data
                data = data.replace('{'+name+'}', value)
                for key in headers:
                    headers[key] = headers[key].replace('{'+name+'}', value)
            for i, (name, value) in enumerate(results.items()):
                old_data = data
                data = data.replace(f'${i+1}', value)
                # print(f'replacing {old_data} with {data} from step results!')
                for key in headers:
                    headers[key] = headers[key].replace(f'${i+1}', value)

            if method == 'post':
                print(f'data after: {data}')

            if method == 'get':
                response = self.session.get(load_url, headers=headers)
            elif method == 'post':
                if 'Content-Type' not in headers:
                    headers['Content-Type'] = 'text/plain'
                response = self.session.post(load_url, headers=headers, data=data.encode('utf-8'))

            # import to nanome if necessary
            if import_type:
                self.import_to_nanome(self.__field_values[last_var], import_type, response.text)
            # save step result
            results[step['name']] = response.text
            if step['resource']['method'] == 'post':
                print(response.text[:500])

        self.set_load_enabled(True)

    def import_to_nanome(self, name, filetype, contents, metadata="{}"):
        try:
            with tempfile.NamedTemporaryFile(mode='w+') as file:
                file.write(contents)
                file.seek(0)
                if filetype == ".pdb":
                    complex = nanome.structure.Complex.io.from_pdb(path=file.name)
                    self.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == ".sdf":
                    complex = nanome.structure.Complex.io.from_sdf(path=file.name)
                    self.bonds_ready(name, metadata, [complex])
                elif filetype == ".cif":
                    complex = nanome.structure.Complex.io.from_mmcif(path=file.name)
                    self.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == '.pdf':
                    self.send_notification(nanome.util.enums.NotificationTypes.error, f"PDF support coming soon")
                    return
                elif filetype == '.nanome':
                    self.send_notification(nanome.util.enums.NotificationTypes.error, f"Workspace support coming soon")
                    return
                    # load workspace
                elif filetype == ".json":
                    complex = nanome.structure.Complex()
                    self.bonds_ready(name, metadata, [complex])
                else:
                    Logs.error("Unknown filetype")
        except: # Making sure temp file gets deleted in case of problem
            self._loading = False
            Logs.error("Error while loading molecule:\n", traceback.format_exc())

    def get_remarks(self, obj):
        dict_found = False
        for value in obj.values():
            if type(value) is dict:
                if not dict_found or len(value) > len(obj):
                    obj = self.get_remarks(value)
                dict_found = True
        return obj

    def bonds_ready(self, name, metadata, complex_list):
        if len(complex_list):
            try:
                print(metadata)
                complex_list[0]._remarks.update(self.get_remarks(json.loads(metadata)))
            except Exception as e:
                print(traceback.format_exc())
                self.send_notification(nanome.util.enums.NotificationTypes.error, f"Metadata error")
            self.add_dssp(complex_list, partial(self.complex_ready, name))

    def complex_ready(self, name, complex_list):
        self._loading = False
        self.send_notification(nanome.util.enums.NotificationTypes.success, f"Successfully loaded while parsing metadata")
        complex_list[0].molecular.name = name
        self.add_to_workspace(complex_list)

def main():
    plugin = nanome.Plugin('URL Loader', 'Load molecule from database', 'Loading', True)
    plugin.set_plugin_class(MakeRequestMenu)
    plugin.run('127.0.0.1', 8888)

if __name__ == '__main__':
    main()