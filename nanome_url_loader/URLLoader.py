import re
import os
from functools import partial

import json
import requests
import tempfile
import traceback

import nanome
from nanome.util import Logs

from .Settings import Settings
from .Authentication import Authentication
from .menus import MakeRequestMenu

##################
##### CONFIG #####
##################

DEFAULT_AUTHENTICATION_URL = ""
DEFAULT_STRUCTURE_URL = "https://files.rcsb.org/download/{MoleculeCode}.cif" # {MoleculeCode} indicates where to write molecule code
DEFAULT_METADATA_URL = "localhost:8080" # {MoleculeCode} indicates where to write molecule code
FILETYPE = "PDB" # PDB / SDF / MMCIF
EXTENSIONS = {"MMCIF": 'cif', "PDB": 'pdb', "SDF": 'sdf'}

##################
##################
##################

MENU_PATH = os.path.join(os.path.dirname(__file__), "json/menus/Main.json")
class URLLoader(nanome.PluginInstance):
    def start(self):
        self._loading = False
        self.__fields = {}

        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)


        self.session = requests.Session()
        self.__settings = Settings(self)
        self.__auth     = Authentication(self, self.__settings, self.session, self.open_menu)
        self.__filetype = FILETYPE

        self.__ln_fields = self.__menu.root.find_node('Fields')
        self.__ln_fields.remove_content()
        self.__type_selector = self.__menu.root.find_node('Type Selector')
        self.__load_btn = self.__menu.root.find_node('Load Button')

        self.setup_menu()
        # self.open_menu()

        if self.__settings.authentication_required:
            self.__auth.open_menu()
        else:
            self.open_menu()

    # def prepare(self, menu=None):

    # When user clicks on "Run", open menu
    def on_run(self):
        self.open_menu()

    def on_advanced_settings(self):
        self.__settings.open_menu()

    def open_menu(self, menu=None):
        self.__menu.enabled = True
        # self.menu = self.__menu
        self.set_file_type(self.__filetype)
        self.render_fields()

    def set_file_type(self, filetype, update=False, button=None):
        self.__filetype = filetype
        # self.__settings.set_extension(EXTENSIONS[filetype])

        for ln_btn in self.__type_selector.get_children():
            btn = ln_btn.get_content()
            btn.selected = btn.text.value.idle == self.__filetype

        if update: self.update_menu(self.__menu)

    def update_fields(self):
        self.__fields.clear()
        for url in self.__settings.get_all().values():
            for field in re.findall('{(.*?)}', url):
                self.__fields[field] = ''

    def setup_menu(self):
        self.__load_btn.forward_dist = 0.02
        for i, ln_btn in enumerate(self.__type_selector.get_children()):
            filetypes = ["MMCIF", "PDB", "SDF"]
            btn = ln_btn.get_content()
            btn.register_pressed_callback(partial(self.set_file_type, filetypes[i], True))
        self.__load_btn.get_content().register_pressed_callback(self.pressed_load)

    def render_fields(self):
        self.__ln_fields.clear_children()
        for field_name, field_value in self.__fields.items():
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
            text_input.placeholder_text = ""
            text_input.max_length = 64
            text_input.register_changed_callback(partial(self.field_changed, field_name))
            self.__ln_fields.add_child(ln)
        self.__ln_fields.create_child_node()
        self.update_menu(self.__menu)

    def field_changed(self, field_name, text_input):
        text_input.input_text = re.sub('([^0-9A-z-._~])', '', text_input.input_text)
        self.__fields[field_name] = text_input.input_text

    def pressed_load(self, button):
        if self._loading == True:
            return
        self._loading = True
        button.text.value.set_all("Loading...")
        button.unusable = True

        self.update_node(self.__ln_fields)

        for field_name, field_value in self.__fields.items():
            if field_value == '':
                self.send_notification(nanome.util.enums.NotificationTypes.error, f"Please set a value for {field_name}")
                return

        self.update_menu(self.__menu)
        self.load_molecule()

    def load_molecule(self):
        structure_url = self.__settings.structure_url
        metadata_url = self.__settings.metadata_url

        if self.__settings.authentication_required and not self.__auth.get_cookie('JSESSIONID'):
            self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Could not authenticate.")
            return

        self.last_structure_field = ""
        for field_name, field_value in self.__fields.items():
            new_structure_url = structure_url.replace("{"+field_name+"}", field_value)
            if new_structure_url != structure_url:
                self.last_structure_field = field_value
            structure_url = new_structure_url
            metadata_url = metadata_url.replace("{"+field_name+"}", field_value)

        response = self.session.get(structure_url)
        try:
            file = tempfile.NamedTemporaryFile(delete=False)
            file.write(response.text.encode("utf-8"))
            file.close()
            if self.__filetype == "PDB":
                complex = nanome.structure.Complex.io.from_pdb(path=file.name)
                self.add_bonds([complex], partial(self.bonds_ready, metadata_url))
            elif self.__filetype == "SDF":
                complex = nanome.structure.Complex.io.from_sdf(path=file.name)
                self.bonds_ready([complex])
            elif self.__filetype == "MMCIF":
                complex = nanome.structure.Complex.io.from_mmcif(path=file.name)
                self.add_bonds([complex], partial(self.bonds_ready, metadata_url))
            else:
                Logs.error("Unknown file self.__filetype")
        except: # Making sure temp file gets deleted in case of problem
            self._loading = False
            Logs.error("Error while loading molecule:\n", traceback.format_exc())

            # attach to complex
        os.remove(file.name)

        self.__load_btn.get_content().text.value.set_all("Load")
        self.__load_btn.get_content().unusable = False
        self.update_menu(self.__menu)

    def get_remarks(self, obj):
        dict_found = False
        for value in obj.values():
            if type(value) is dict:
                if not dict_found or len(value) > len(obj):
                    obj = self.get_remarks(value)
                dict_found = True
        return obj

    def bonds_ready(self, metadata_url, complex_list):
        if len(complex_list):
            try:
                response = self.session.get(metadata_url)
                metadata = json.loads(response.text.encode("utf-8"))
                complex_list[0]._remarks.update(self.get_remarks(metadata))
            except Exception as e:
                print(traceback.format_exc())
                self.send_notification(nanome.util.enums.NotificationTypes.error, f"Metadata error")

        self.add_dssp(complex_list, self.complex_ready)

    def complex_ready(self, complex_list):
        self._loading = False
        self.send_notification(nanome.util.enums.NotificationTypes.success, f"Successfully loaded while parsing metadata")
        complex_list[0].molecular.name = self.last_structure_field
        self.add_to_workspace(complex_list)

def main():
    plugin = nanome.Plugin("URL Loader", "Load molecule from database", "Loading", True)
    plugin.set_plugin_class(MakeRequestMenu)
    plugin.run('127.0.0.1', 8888)

if __name__ == "__main__":
    main()