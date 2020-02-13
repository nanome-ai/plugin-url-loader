import re
import json
import os
from functools import partial

import nanome
BASE_PATH = os.path.dirname(os.path.realpath(__file__))
MENU_PATH = os.path.join(BASE_PATH, 'json', 'menus', 'Settings.json')
OFF_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'off.png')
ON_ICON_PATH = os.path.join(BASE_PATH, 'assets', 'icons', 'on.png')

class Settings():
    def __init__(self, plugin, default_authentication_url, default_load_url, default_metadata_url):
        self.__plugin = plugin
        self.authentication_required = True
        self.authentication_url = default_authentication_url
        self.structure_url = default_load_url
        self.metadata_url = default_metadata_url

        self.__settings_path = os.path.normpath(os.path.join(plugin.plugin_files_path, 'url-loader', 'settings.json'))
        if not os.path.exists(os.path.dirname(self.__settings_path)):
            os.makedirs(os.path.dirname(self.__settings_path))

        self.__settings = {'authentication_url': self.authentication_url, 'structure_url': self.structure_url, 'metadata_url': self.metadata_url}

        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.__menu.register_closed_callback(plugin.open_menu)

        self.inp_authentication = self.__menu.root.find_node('Authentication URL Input').get_content()
        self.inp_authentication.register_changed_callback(partial(self.update_fields, 'authentication', True))
        self.inp_authentication.register_submitted_callback(self.save_settings)

        self.ln_require_auth = self.__menu.root.find_node('Authentication Required Button')
        self.ln_require_auth.forward_dist = 0.002

        # Auth on by default
        btn_auth = self.ln_require_auth.get_content()
        btn_auth.selected = self.authentication_required
        btn_auth.register_pressed_callback(partial(self.toggle_auth_required, self.ln_require_auth))
        btn_auth.outline.active = False
        ln_image = self.ln_require_auth.find_node('Image')
        ln_image.forward_dist = -0.002
        img = ln_image.add_new_image(ON_ICON_PATH if btn_auth.selected else OFF_ICON_PATH)

        self.inp_structure = self.__menu.root.find_node('Structure URL Input').get_content()
        self.inp_structure.register_changed_callback(partial(self.update_fields, 'structure', True))
        self.inp_structure.register_submitted_callback(self.save_settings)

        self.inp_metadata = self.__menu.root.find_node('Metadata URL Input').get_content()
        self.inp_metadata.register_changed_callback(partial(self.update_fields, 'metadata', True))
        self.inp_metadata.register_submitted_callback(self.save_settings)

        self.__ln_save = self.__menu.root.find_node('Save Button')
        self.__ln_save.get_content().register_pressed_callback(self.save_settings)

        self.load_settings()

    def open_menu(self):
        self.load_settings()
        for field in ['authentication', 'structure', 'metadata']:
            self.update_fields(field, field=='metadata')
        self.__menu.enabled = True
        self.__menu.index = 1
        self.__plugin.update_menu(self.__menu)

    def save_settings(self, menu=None):
        with open(self.__settings_path, 'w') as settings:
            json.dump(self.__settings, settings)

        self.__plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Settings saved.")
        self.__plugin.render_fields()

    def load_settings(self, update=False):
        if os.path.exists(self.__settings_path):
            with open(self.__settings_path, 'r') as file_settings:
                settings = json.load(file_settings)
                self.authentication_url = settings.get('authentication_url', self.authentication_url)
                self.structure_url = settings.get('structure_url', self.structure_url)
                self.metadata_url = settings.get('metadata_url', self.metadata_url)

        self.inp_authentication.input_text = self.authentication_url
        self.inp_structure.input_text = self.structure_url
        self.inp_metadata.input_text = self.metadata_url

        if update:
            self.__plugin.update_menu(self.__menu)

    def update_fields(self, name, render=True, text_input=None):
        # clean
        text_input = text_input or getattr(self, 'inp_' + name)
        text_input.input_text = re.sub("([^0-9A-z-._~:/\{\}])", '', text_input.input_text)
        # set
        setting = name+'_url'
        setattr(self, setting, text_input.input_text)
        self.__settings[setting] = text_input.input_text
        self.__plugin.update_fields()

        # render
        if render:
            self.__plugin.render_fields()

    def set_extension(self, ext):
        self.structure_url = re.sub('\.(cif|pdb|sdf)', f'.{ext}', self.structure_url)

    def toggle_auth_required(self, ln, button):
        button.selected = not button.selected
        print(f'selected: {button.selected}')
        self.authentication_required = button.selected
        img = ln.find_node('Image').get_content()
        img.file_path = ON_ICON_PATH if button.selected else OFF_ICON_PATH
        self.__plugin.update_node(ln)

    def get_all(self):
        return self.__settings