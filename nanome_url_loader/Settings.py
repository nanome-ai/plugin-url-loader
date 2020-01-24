import re
from os import path

import nanome

MENU_PATH = path.join(path.dirname(path.realpath(__file__)), "json/menus/settings.json")

class Settings():

  def __init__(self, plugin, default_load_url, default_metadata_url):
    self.__plugin = plugin
    self.structure_url = default_load_url
    self.metadata_url = default_metadata_url
    self.__plugin.set_structure_field_names(re.findall('{{(.*?)}}', self.structure_url))
    self.__plugin.set_metadata_field_names(re.findall('{{(.*?)}}', self.metadata_url))

    self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
    self.__menu.register_closed_callback(plugin.open_menu)

    self.__ln_structure_input = self.__menu.root.find_node('Structure URL Input')
    self.__ln_structure_input.get_content().register_changed_callback(self.update_structure_fields)
    self.__ln_structure_input.get_content().register_submitted_callback(self.save_url)

    self.__ln_metadata_input = self.__menu.root.find_node('Metadata URL Input')
    self.__ln_metadata_input.get_content().register_changed_callback(self.update_metadata_fields)
    self.__ln_metadata_input.get_content().register_submitted_callback(self.save_url)

    self.__ln_save = self.__menu.root.find_node('Save Button')
    self.__ln_save.get_content().register_pressed_callback(self.save_url)

    self.try_load_url()
    self.update_structure_fields()
    self.update_metadata_fields()

  def open_menu(self):
    self.try_load_url()
    self.update_structure_fields()
    self.__menu.enabled = True
    self.__menu.index = 1
    self.__plugin.menu = self.__menu
    self.__plugin.update_menu(self.__menu)

  def save_url(self, menu=None):
    with open('structure_settings.txt', 'w') as structure_settings:
      structure_settings.write(self.__ln_structure_input.get_content().input_text)

    with open('metadata_settings.txt', 'w') as metadata_settings:
      metadata_settings.write(self.__ln_metadata_input.get_content().input_text)

    self.__plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Settings saved.")

  def try_load_url(self, update=False):
    if path.exists ('structure_settings.txt'):
      with open('structure_settings.txt', 'r') as structure_settings:
        self.structure_url = structure_settings.readlines()[0] or self.structure_url

    if path.exists ('metadata_settings.txt'):
      with open('metadata_settings.txt', 'r') as metadata_settings:
        self.metadata_url = metadata_settings.readlines()[0] or self.metadata_url

    self.__ln_structure_input.get_content().input_text = self.structure_url
    self.__ln_metadata_input.get_content().input_text = self.metadata_url

    if update: self.__plugin.update_menu(self.__menu)

  def update_structure_fields(self, text_input=None):
      text_input = text_input or self.__ln_structure_input.get_content()
      text_input.input_text = re.sub("([^0-9A-z-._~:/\{\}])", '', text_input.input_text)
      print(f'updated structure input text to {text_input.input_text}')
      self.structure_url = text_input.input_text
      self.__plugin.set_structure_field_names(re.findall('{{(.*?)}}', self.structure_url))

  def update_metadata_fields(self, text_input=None):
      text_input = text_input or self.__ln_metadata_input.get_content()
      text_input.input_text = re.sub("([^0-9A-z-._~:/\{\}])", '', text_input.input_text)
      print(f'updated metadata input text to {text_input.input_text}')
      self.metadata_url = text_input.input_text
      self.__plugin.set_metadata_field_names(re.findall('{{(.*?)}}', self.metadata_url))

  def set_extension(self, ext):
    self.structure_url = re.sub('\.(cif|pdb|sdf)', f'.{ext}', self.structure_url)