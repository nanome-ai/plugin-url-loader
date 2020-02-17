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

from . import ResourcesMenu
from . import RequestsMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), 'json', 'MakeRequest.json')
class MakeRequestMenu():
    def __init__(self, plugin, settings, show_all_requests=True):
        self.session = requests.Session()
        self.proxies = {
            'no': 'pass'
        }
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 0
        self.plugin = plugin
        self.settings = settings
        self.field_names = set()
        self.field_values = {}

        self.request = None

        self.__ln_fields = self.menu.root.find_node('Fields')
        self.ln_all_requests = self.menu.root.find_node('All Requests')
        self.ln_all_requests.get_content().register_pressed_callback(lambda b: self.plugin.requests.open_menu())
        self.ln_all_requests.enabled = show_all_requests
        self.btn_load = self.menu.root.find_node('Load Button').get_content()
        self.btn_load.register_pressed_callback(self.load_request)

    def open_menu(self):
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)

    def show_request(self):
        self.__ln_fields.clear_children()
        if not self.request:
            self.plugin.update_menu(self.menu)
            return

        self.field_names = self.settings.get_variables(self.request)
        self.field_values = {name:'' for name in self.field_names}
        for field_name in self.field_names:
            field_value = self.field_values.get(field_name, '')
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
        self.plugin.update_menu(self.menu)

    def field_changed(self, field_name, text_input):
        self.field_values[field_name] = text_input.input_text
        self.settings.set_variable(field_name, text_input.input_text)

    def clean_field(self, name, update=False, text_input=None):
        value = text_input.input_text if text_input else self.field_values[name]
        self.field_values[name] = re.sub('([^0-9A-z-._~{}$])', '', value)
        self.settings.set_variable(name, value)
        self.plugin.update_node(self.__ln_fields)

    def set_load_enabled(self, enabled):
        self.btn_load.unusable = not enabled
        self.plugin.update_content(self.btn_load)

    def contextualize(self, variable, contexts):
        for name in self.settings.extract_variables(variable):
            value = self.settings.get_variable(name)
            variable = variable.replace('{{'+name+'}}', value)
        return variable

    def get_response(self, resource, contexts, data=None):
        load_url = resource['url']
        method = resource['method'].lower()
        headers = resource['headers']
        data = data or resource['data']
        load_url = self.contextualize(variable=load_url, contexts=contexts)
        print(f'contextualizing headers... {headers}')
        headers = {name:self.contextualize(value, contexts) for name,value in headers.items()}
        print('contextualizing data...')
        data = self.contextualize(data, contexts=contexts)
        headers.update({'Content-Length': str(len(data))})

        if method == 'get':
            print(f'load_url: {load_url}')
            response = self.session.get(load_url, proxies=self.proxies, verify=False)
        elif method == 'post':
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'text/plain'
            print(f'resource: {resource}')
            response = self.session.post(load_url, data=data.encode('utf-8'), proxies=self.proxies, verify=False)
        
        out_name, out_value = self.set_response_vars(resource, response.text)
        return response, (out_name, out_value)

    def set_response_vars(self, resource, response_text):
        try:
            json_response = json.loads(response_text)
            for var_name, var_path in resource['output variables'].items():
                var_value = json_response
                for path_part in var_path:
                    var_value = var_value[path_part]
                self.settings.set_variable(var_name, var_value)
                return var_name, var_value
        except:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Cannot link resource output to {var_name}")
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Is the resource returning something other than JSON?")
        return None, None
    
    def load_request(self, button=None):
        if not self.request:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.message, "Please select a request")
            return

        for name in self.field_names:
            self.clean_field(name)

        self.set_load_enabled(False)
        results = {}
        for i, step in enumerate(self.request['steps']):
            resource = self.settings.get_resource_by_id(step['resource'])
            import_type = resource['import type']
            metadata = step['metadata_source']
            data = resource['data'].replace("\'", "\"")
            # override data if necessary
            data_override_field_name = f"{self.request['name']} {step['name']} data"
            if step['override_data']:
                data = self.field_values[data_override_field_name]

            contexts = [self.settings.variables, self.field_values, results]
            response, (out_var, out_value) = self.get_response(resource, contexts, data)
            print(f'response: {response.text}')
            import_name = self.contextualize(variable=resource['import name'], contexts=contexts)
            if import_type: self.import_to_nanome(import_name, import_type, response.text, metadata)
            results[f'step{i+1}'] = out_value or response.text
        self.set_load_enabled(True)

    def import_to_nanome(self, name, filetype, contents, metadata):
        try:
            with tempfile.NamedTemporaryFile(mode='w+') as file:
                file.write(contents)
                file.seek(0)
                if filetype == ".pdb":
                    complex = nanome.structure.Complex.io.from_pdb(path=file.name)
                    self.plugin.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == ".sdf":
                    complex = nanome.structure.Complex.io.from_sdf(path=file.name)
                    self.bonds_ready(name, metadata, [complex])
                elif filetype == ".cif":
                    complex = nanome.structure.Complex.io.from_mmcif(path=file.name)
                    self.plugin.add_bonds([complex], partial(self.bonds_ready, name, metadata))
                elif filetype == '.pdf':
                    self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"PDF support coming soon")
                    return
                elif filetype == '.nanome':
                    self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Workspace support coming soon")
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
                complex_list[0]._remarks.update(self.get_remarks(json.loads(metadata)))
            except Exception as e:
                print(traceback.format_exc())
                self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Metadata error")
            self.plugin.add_dssp(complex_list, partial(self.complex_ready, name))

    def complex_ready(self, name, complex_list):
        self._loading = False
        self.plugin.send_notification(nanome.util.enums.NotificationTypes.success, f"Successfully loaded while parsing metadata")
        complex_list[0].molecular.name = name
        self.plugin.add_to_workspace(complex_list)