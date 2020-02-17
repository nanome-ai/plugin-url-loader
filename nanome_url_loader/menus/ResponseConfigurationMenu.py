import os
import json
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement
from . import RequestConfigurationMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "ResponseConfig.json")

class ResponseConfigurationMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 5

        self.resource = None
        self.response = None

        self.lst_response_elements = self.menu.root.find_node("Response Entry List").get_content()

    def open_menu(self, resource=None):
        self.set_resource(resource)
        self.show_hierarchy()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)

    def set_resource(self, resource):
      self.resource = resource

    def get_response(self):
      self.response = self.plugin.get_response(self.resource, self.settings.variables)

    def show_hierarchy(self):
      if not self.response:
        self.get_response()

      if self.response:
        obj = json.loads(self.response)
        self.draw_elements(0, obj)
        
    def draw_elements(start_index, obj, path=None):
      if not path:
        path = ['first']

      for i, element in enumerate(obj):
        path[-1] = element
        if type(element) in [list, dict]:
          path.append('next')
          self.draw_elements(start_index, element, path)
        else:
          self.create_button(i, len(path)-1, str(element), path)
          start_index += 1

    def create_button(self, index, indentation, text, json_path=None):
      ln = nanome.ui.LayoutNode()
      ln.set_padding(left=indentation*0.1)
      btn = ln.add_new_button(text)
      btn.json_path = json_path
      btn.text.horizontal_align = btn.HorizAlignOptions.Middle
      btn.register_pressed_callback(self.open_variable_setup)
      self.lst_response_elements.items.insert(index, ln)

    def open_variable_setup(self, button):
      print(f'Are you sure you want to create a variable for {btn.name}?')
      print(f'variable path: {button.json_path}')