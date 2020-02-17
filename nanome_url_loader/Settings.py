import re
import json
import os
from functools import partial

import nanome
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
MENU_PATH = os.path.join(BASE_PATH, 'menus', 'json', 'Settings.json')
OFF_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'off.png')
ON_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'on.png')

class Settings():

    def __init__(self, plugin):
        self.__plugin = plugin
        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.__menu.register_closed_callback(plugin.open_menu)

        self.variables = {}
        self.resource_names = []
        self.resources = {}
        self.rsrc_i = 1
        self.request_names = []
        self.requests = {}
        self.__settings = {}

        self.__settings_path = os.path.normpath(os.path.join(plugin.plugin_files_path, 'url-loader', 'settings.json'))
        print(f'settings: {self.__settings_path}')
        if not os.path.exists(os.path.dirname(self.__settings_path)):
            os.makedirs(os.path.dirname(self.__settings_path))
        self.load_settings()

    def generate_settings(self):
        for setting_name in ['variables', 'resource_names', 'resources', 'rsrc_i', 'request_names', 'requests']:
            yield setting_name, getattr(self, setting_name)

    def load_settings(self, update=False):
        if os.path.exists(self.__settings_path):
            with open(self.__settings_path, 'r') as settings_file:
                settings = json.load(settings_file)
                for key, value in settings.items():
                    setattr(self, key, value)
        if update:
            self.__plugin.update_menu(self.__menu)

    def save_settings(self, menu=None):
        with open(self.__settings_path, 'w') as settings_file:
            json.dump(dict(self.generate_settings()), settings_file)
        self.__plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Settings saved.")

    def extract_variables(self, url):
        fields = []
        for field in re.findall('{(.*?)}', url):
            fields.append(field)
            self.touch_variable(field)
        return fields

    def touch_variables(self, var_names):
        for var_name in var_names:
            if var_name not in self.variables:
                self.variables[var_name] = ''

    def set_variable(self, name, value):
        self.variables[name] = value

    def get_variable(self, name):
        if name not in self.variables:
            self.touch_variables([name])
        return self.variables[name]

    def get_variables(self, request):
        for step in request['steps']:
            for var_name in step['resource']['variables']:
                yield var_name, self.get_variable(var_name)
            if step['override_data']:
                override_data_name = f"{request['name']} {step['name']} data"
                yield override_data_name, self.get_variable(override_data_name)

    def delete_variable(self, var_name):
        del self.variables[var_name]

    def add_resource(self, name, url, method, import_type=None, headers={'Content-Type':'text/plain'}, data=''):
        self.rsrc_i += 1
        variables = self.extract_variables(url)
        if name not in self.resource_names:
            self.resource_names.append(name)
            self.resources[name] = {
                'name': name,
                'url': url,
                'variables': variables,
                'method': method,
                'import type': import_type,
                'headers': headers,
                'data': data,
                'references': {}
            }
        return self.resources[name]

    def create_empty_resource():
        name = f'Resource {self.rsrc_i}'
        self.rsrc_i += 1
        self.resource_names.append(name)
        self.resources[name] = {
            'name': name,
            'url': '',
            'variables': [],
            'method': 'get',
            'import type': '.json',
            'headers': {'Content-Type':'text/plain'},
            'data': None,
            'references': {}
        }
        return self.resources[name]

    def delete_resource(self, resource):
        has_references = len(list(filter(lambda x: x > 0, [value for value in resource['references'].values()]))) > 0
        if not has_references:
            self.resource_names.remove(resource['name'])
            del resource
            return True
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource in use")
            return False

    def rename_resource(self, resource, new_name):
        old_name = resource['name']
        self.resource_names[self.resource_names.index(old_name)] = new_name
        self.resources[new_name] = resource
        resource['name'] = new_name
        del self.resources[old_name]
        return True

    def change_resource_url(self, resource, new_url):
        resource['url'] = new_url
        resource['variables'] = self.extract_variables(new_url)
        return True

    def add_request(self, name):
        if name not in self.requests:
            self.request_names.append(name)
            self.requests[name] = {'name': name, 'steps': [], 'step names': {}}
            return True
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Please choose a unique name")
            return False

    def rename_request(self, request, new_name):
        old_name = request['name']
        self.request_names[self.request_names.index(old_name)] = new_name
        self.requests[new_name] = request
        self.requests[new_name]['name'] = new_name
        del self.requests[old_name]
        return True

    def delete_request(self, name):
        for i, step in enumerate(self.requests[name]['steps']):
            self.delete_step(name, i)
        self.request_names.remove(name)
        del self.requests[name]
        return True

    def add_step(self, request_name, step_name, resource_name, metadata_source='', override_data=False):
        request = self.requests[request_name]
        if step_name not in request['step names']:
            request['step names'][step_name] = True
            step = {'name': step_name, 'resource': self.resources[resource_name], 'override_data': override_data, 'metadata_source': metadata_source}
            request['steps'].append(step)
            refs = self.resources[resource_name]['references']
            refs[request_name] = refs.get(request_name, 0) + 1
            return step
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Please choose a unique name")
            return False

    def rename_step(self, request_name, step, new_step_name):
        request = self.requests[request_name]
        step_name = step['name']
        if step_name in request['step names']:
            del request['step names'][step_name]
            request['step names'][new_step_name] = True
            for a_step in request['steps']:
                if a_step['name'] == step_name:
                    a_step['name'] = new_step_name
                    return True
        else:
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Step does not exist")
            return False

    def move_step(self, request_name, step_index, new_index):
        self.requests[request_name]['steps'].insert(new_index, self.requests[request_name]['steps'].pop(step_index))

    def delete_step(self, request_name, step_index):
        request = self.requests[request_name]
        name = request['steps'][step_index]['name']
        refs = request['steps'][step_index]['resource']['references']
        if refs.get(request_name, None) == 0:
            del request['steps'][step_index]['resource']['references'][request_name]
        else:
            refs[request_name] = refs.get(request_name, 1) - 1
        del request['step names'][name]
        del request['steps'][step_index]
        return True