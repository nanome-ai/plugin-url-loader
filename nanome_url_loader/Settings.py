import re
from os import path

import nanome

MENU_PATH = path.join(path.dirname(path.realpath(__file__)), "json/menus/settings.json")

class Settings():

  def __init__(self, plugin, default_load_url):
    self.__plugin = plugin
    self.load_url = default_load_url
    self.__plugin.set_field_names(re.findall('{{(.*?)}}', self.load_url))

    self.__menu = nanome.ui.Menu.io.from_json(MENU_PATH)
    self.__menu.register_closed_callback(plugin.open_menu)

    self.__ln_input = self.__menu.root.find_node('URL Input')
    self.__ln_input.get_content().register_changed_callback(self.update_user_fields)

    self.__ln_save = self.__menu.root.find_node('Save Button')
    self.__ln_save.get_content().register_pressed_callback(plugin.open_menu)

  def open_menu(self):
    self.__menu.enabled = True
    self.__menu.index = 1
    self.__plugin.menu = self.__menu

  def update_user_fields(self, text_input):
      text_input.input_text = re.sub('([^0-9A-z-._~])', '', text_input.input_text)
      self.load_url = text_input.input_text
      self.__plugin.set_field_names(re.findall('{{(.*?)}}', self.load_url))