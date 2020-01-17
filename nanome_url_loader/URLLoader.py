import requests
import tempfile
import traceback
import os
from os import path
from functools import partial

import nanome
from nanome.util import Logs

from .Settings import Settings

##################
##### CONFIG #####
##################

default_url = "https://files.rcsb.org/download/{{MoleculeCode}}.cif" # {{NAME}} indicates where to write molecule code
type = "MMCIF" # PDB / SDF / MMCIF

##################
##################
##################

MENU_PATH = path.join(path.dirname(path.realpath(__file__)), "json/menus/Main.json")
class URLLoader(nanome.PluginInstance):
    def start(self):
        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.__settings = Settings(self, default_url)

        self._loading = False
        self.__fields = []
        self.__field_names = []
        self.__field_values = []

        self.__field_container = self.__menu.root.find_node('Fields')
        self.__load_btn = self.__menu.root.find_node('Load Button')
        self.__load_btn.get_content().register_pressed_callback(self.pressed_load)

        self.open_menu()

    # When user clicks on "Run", open menu
    def on_run(self):
        self.open_menu()

    def on_advanced_settings(self):
        self.__settings.open_menu()

    def open_menu(self, menu=None):
        self.__menu.enabled = True
        self.menu = self.__menu
        self.render_fields()
        self.update_menu(self.menu)

    def set_field_names(self, fields):
        self.__field_names = fields
        self.__field_values = []

    def render_fields(self):
        self.__fields = []
        self.__field_container.clear_children()
        for i, field_name in enumerate(self.__field_names):
            ln_button = self.__field_container.create_child_node()
            ln_button.forward_dist = .03
            ln_button.set_padding(top=0.07, down=0.04)

            # Create a text input for each field
            input_field = ln_field.add_new_text_input()
            input_field.placeholder_text = field_name
            input_field.register_changed_callback(partial(self.field_changed, field_index))
            self.__fields.append(input_field)
        
        self.update_menu(self.__menu)

    def field_changed(self, field_index, text_input):
        text_input.input_text = re.sub('([^0-9A-z-._~])', '', text_input.input_text)
        self.__field_values[field_index] = text_input.input_text

    def pressed_load(self, button):
        if self._loading == True:
            return
        self._loading = True
        if self.__field.input_text:
            self.load_molecule(self.__field.input_text)

    def load_molecule(self):
        url = settings.load_url
        for i, field_name in enumerate(self.__field_names):
            url = url.replace("{{"+field_name+"}}", self.__field_values[i])
        response = requests.get(url_to_load)
        file = tempfile.NamedTemporaryFile(delete=False)
        self._name = self.__field_values[-1]
        try:
            file.write(response.text.encode("utf-8"))
            file.close()
            if type == "PDB":
                complex = nanome.structure.Complex.io.from_pdb(path=file.name)
                self.add_bonds([complex], self.bonds_ready)
            elif type == "SDF":
                complex = nanome.structure.Complex.io.from_sdf(path=file.name)
                self.bonds_ready([complex])
            elif type == "MMCIF":
                complex = nanome.structure.Complex.io.from_mmcif(path=file.name)
                self.add_bonds([complex], self.bonds_ready)
            else:
                Logs.error("Unknown file type")
        except: # Making sure temp file gets deleted in case of problem
            self._loading = False
            Logs.error("Error while loading molecule:\n", traceback.format_exc())
        os.remove(file.name)

    def bonds_ready(self, complex_list):
        self.add_dssp(complex_list, self.complex_ready)

    def complex_ready(self, complex_list):
        self._loading = False
        complex_list[0].molecular.name = self._name
        self.add_to_workspace(complex_list)

def main():
    plugin = nanome.Plugin("URL Loader", "Load molecule from database", "Loading", True)
    plugin.set_plugin_class(URLLoader)
    plugin.run('127.0.0.1', 8888)

if __name__ == "__main__":
    main()