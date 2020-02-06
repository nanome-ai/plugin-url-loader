import re
from os import path
from functools import partial

import nanome

MENU_PATH = path.join(path.dirname(path.realpath(__file__)), "json/menus/Settings.json")

class Settings():

  def __init__(self, plugin, default_load_url, default_metadata_url):
    self.__plugin = plugin
    self.structure_url = default_load_url
    self.metadata_url = default_metadata_url

    self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
    self.__menu.register_closed_callback(plugin.open_menu)

    # TODO remove for 1.16
    self.__plugin.menu.root.get_children().append(self.__menu.root)

    self.inp_structure = self.__menu.root.find_node('Structure URL Input').get_content()
    self.inp_structure.register_changed_callback(partial(self.update_fields, 'structure'))
    self.inp_structure.register_submitted_callback(self.save_url)

    self.inp_metadata = self.__menu.root.find_node('Metadata URL Input').get_content()
    self.inp_metadata.register_changed_callback(partial(self.update_fields, 'metadata'))
    self.inp_metadata.register_submitted_callback(self.save_url)

    self.__ln_save = self.__menu.root.find_node('Save Button')
    self.__ln_save.get_content().register_pressed_callback(self.save_url)

    self.try_load_url()

  def open_menu(self):
    self.try_load_url()
    self.update_fields('structure')
    self.update_fields('metadata')
    self.__menu.enabled = True
    self.__menu.index = 1
    self.__plugin.update_menu(self.__menu)

  def save_url(self, menu=None):
    with open('structure_settings.txt', 'w') as structure_settings:
      structure_settings.write(self.inp_structure.input_text)

    with open('metadata_settings.txt', 'w') as metadata_settings:
      metadata_settings.write(self.inp_metadata.input_text)

    self.__plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Settings saved.")
    self.__plugin.render_fields()

  def try_load_url(self, update=False):
    if path.exists ('structure_settings.txt'):
      with open('structure_settings.txt', 'r') as structure_settings:
        self.structure_url = structure_settings.readlines()[0] or self.structure_url

    if path.exists ('metadata_settings.txt'):
      with open('metadata_settings.txt', 'r') as metadata_settings:
        self.metadata_url = metadata_settings.readlines()[0] or self.metadata_url

    self.inp_structure.input_text = self.structure_url
    self.inp_metadata.input_text = self.metadata_url

    if update: self.__plugin.update_menu(self.__menu)

  def update_fields(self, name, text_input=None):
      text_input = text_input or getattr(self, 'inp_' + name)
      text_input.input_text = re.sub("([^0-9A-z-._~:/\{\}])", '', text_input.input_text)
      setattr(self, name + '_url', text_input.input_text)
      self.__plugin.parse_fields()
      self.__plugin.render_fields()

  def set_extension(self, ext):
    self.structure_url = re.sub('\.(cif|pdb|sdf)', f'.{ext}', self.structure_url)