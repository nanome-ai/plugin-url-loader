import requests
import tempfile
import traceback
import re
import os
from os import path
from functools import partial

import nanome
from nanome.util import Logs

from .Settings import Settings

##################
##### CONFIG #####
##################

DEFAULT_STRUCTURE_URL = "https://files.rcsb.org/download/{{MoleculeCode}}.cif" # {{MoleculeCode}} indicates where to write molecule code
DEFAULT_METADATA_URL = "https://files.rcsb.org/metadata/{{MoleculeCode}}.json" # {{MoleculeCode}} indicates where to write molecule code
FILETYPE = "PDB" # PDB / SDF / MMCIF
EXTENSIONS = {"MMCIF": 'cif', "PDB": 'pdb', "SDF": 'sdf'}

##################
##################
##################

MENU_PATH = path.join(path.dirname(path.realpath(__file__)), "json/menus/Main.json")
class URLLoader(nanome.PluginInstance):
    def start(self):
        self._loading = False
        self.__structure_fields = []
        self.__metadata_fields  = []
        self.__structure_field_names = []
        self.__structure_field_values = []
        self.__metadata_field_names = []
        self.__metadata_field_values = []

        self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.__settings = Settings(self, DEFAULT_STRUCTURE_URL, DEFAULT_METADATA_URL)
        self.__filetype = FILETYPE

        self.__structure_field_container = self.__menu.root.find_node('Structure Fields')
        self.__metadata_field_container  = self.__menu.root.find_node('Metadata Fields')
        self.__type_selector = self.__menu.root.find_node('Type Selector')
        self.__load_btn = self.__menu.root.find_node('Load Button')

        self.setup_menu()
        self.open_menu()

    # When user clicks on "Run", open menu
    def on_run(self):
        self.open_menu()

    def on_advanced_settings(self):
        self.__settings.open_menu()

    def open_menu(self, menu=None):
        self.__menu.enabled = True
        self.menu = self.__menu
        self.set_file_type(self.__filetype)
        self.render_structure_fields()
        self.render_metadata_fields(update=True)

    def set_structure_field_names(self, fields):
        self.__structure_field_names = fields
        self.__structure_field_values = ['']*len(fields)
        print(f'structure field names set to {self.__structure_field_names}')

    def set_metadata_field_names(self, fields):
        self.__metadata_field_names = fields
        self.__metadata_field_values = ['']*len(fields)
        print(f'metadata field names set to {self.__metadata_field_names}')


    def set_file_type(self, filetype, update=False, button=None):
        self.__filetype = filetype
        self.__settings.set_extension(EXTENSIONS[filetype])

        for ln_btn in self.__type_selector.get_children():
            btn = ln_btn.get_content()
            btn.selected = btn.text.value.idle == self.__filetype

        if update: self.update_menu(self.__menu)
        print(f'file type is now {self.__filetype}')

    def setup_menu(self):
        self.__load_btn.forward_dist = 0.02
        for i, ln_btn in enumerate(self.__type_selector.get_children()):
            filetypes = ["MMCIF", "PDB", "SDF"]
            btn = ln_btn.get_content()
            btn.register_pressed_callback(partial(self.set_file_type, filetypes[i], True))
        self.__load_btn.get_content().register_pressed_callback(self.pressed_load)

    def render_structure_fields(self, update=False):
        print(f'field names are: {self.__structure_field_names}')
        print(f'field values are: {self.__structure_field_values}')
        self.__structure_fields = []
        self.__structure_field_container.clear_children()
        for field_index, field_name in enumerate(self.__structure_field_names):
            ln = self.__structure_field_container.create_child_node(field_name)
            ln.layout_orientation = nanome.util.enums.LayoutTypes.horizontal
            ln.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)

            ln_label = ln.create_child_node()
            label = ln_label.add_new_label(field_name+':')
            label.text_max_size = 0.4
            label.text_vertical_align = nanome.util.enums.VertAlignOptions.Middle
            ln_field = ln.create_child_node()
            ln_field.forward_dist = 0.02
            ln_field.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)
            input_field = ln_field.add_new_text_input()
            input_field.placeholder_text = ""
            input_field.register_changed_callback(partial(self.structure_field_changed, field_index))
            self.__structure_fields.append(input_field)
        if update: self.update_menu(self.__menu)


    def render_metadata_fields(self, update=False):
        print(f'field names are: {self.__structure_field_names}')
        print(f'field values are: {self.__structure_field_values}')
        self.__metadata_fields = []
        self.__metadata_field_container.clear_children()
        for field_index, field_name in enumerate(self.__metadata_field_names):
            ln = self.__metadata_field_container.create_child_node(field_name)
            ln.layout_orientation = nanome.util.enums.LayoutTypes.horizontal
            ln.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)

            ln_label = ln.create_child_node()
            label = ln_label.add_new_label(field_name+':')
            label.text_max_size = 0.4
            label.text_vertical_align = nanome.util.enums.VertAlignOptions.Middle
            ln_field = ln.create_child_node()
            ln_field.forward_dist = 0.02
            ln_field.set_padding(top=0.01, down=0.01, left=0.01, right=0.01)
            input_field = ln_field.add_new_text_input()
            input_field.placeholder_text = ""
            input_field.register_changed_callback(partial(self.metadata_field_changed, field_index))
            self.__metadata_fields.append(input_field)
        if update: self.update_menu(self.__menu)


    def structure_field_changed(self, field_index, text_input):
        text_input.input_text = re.sub('([^0-9A-z-._~])', '', text_input.input_text)
        self.__structure_field_values[field_index] = text_input.input_text

    def metadata_field_changed(self, field_index, text_input):
        text_input.input_text = re.sub('([^0-9A-z-._~])', '', text_input.input_text)
        self.__metadata_field_values[field_index] = text_input.input_text

    def pressed_load(self, button):
        if self._loading == True:
            return
        self._loading = True
        button.text.value.set_all("Loading...")
        button.unusable = True

        for i, field_value in enumerate(self.__structure_field_values):
            if field_value == '':
                self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, f"Please set a value for {self.__structure_field_names[i]}")
                return

        self.update_menu(self.__menu)
        self.load_molecule()

    def load_molecule(self):
        structure_url = self.__settings.structure_url
        metadata_url = self.__settings.metadata_url
        for i, field_name in enumerate(self.__structure_field_names):
            structure_url = structure_url.replace("{{"+field_name+"}}", self.__structure_field_values[i])
        for i, field_name in enumerate(self.__metadata_field_names):
                print(f'metadata_url: {metadata_url}')
                metadata_url = self.__settings.metadata_url.replace("{{"+field_name+"}}", self.__metadata_field_values[i])

        print(f'structure_url: {structure_url}')
        response = requests.get(structure_url)
        file = tempfile.NamedTemporaryFile(delete=False)
        self._name = self.__structure_field_values[-1]
        try:
            file.write(response.text.encode("utf-8"))
            file.close()
            if self.__filetype == "PDB":
                complex = nanome.structure.Complex.io.from_pdb(path=file.name)
                complex._remarks['source'] = structure_url
                self.add_bonds([complex], partial(self.bonds_ready, structure_url, metadata_url))
            elif self.__filetype == "SDF":
                complex = nanome.structure.Complex.io.from_sdf(path=file.name)
                self.bonds_ready([complex])
            elif self.__filetype == "MMCIF":
                complex = nanome.structure.Complex.io.from_mmcif(path=file.name)
                complex._remarks['source'] = structure_url
                self.add_bonds([complex], partial(self.bonds_ready, structure_url, metadata_url))
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

    def bonds_ready(self, structure_url, metadata_url, complex_list):
        if len(complex_list):
            complex_list[0]._remarks['source'] = structure_url
            complex_list[0]._remarks['metadata_source'] = metadata_url

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