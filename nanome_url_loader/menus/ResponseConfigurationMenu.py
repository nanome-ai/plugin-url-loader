import os
import json
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "ResponseConfig.json")
RESPONSE_SETUP = os.path.join(os.path.dirname(__file__), "json", "MakeRequest.json")

class ResponseConfigurationMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 5
        self.response_setup = nanome.ui.Menu(self.menu.index+1, 'Response Setup')
        self.variable_confirm = nanome.ui.Menu(self.menu.index+2, 'Confirm Response Variable')

        self.resource = None
        self.response = None

        self.lst_response_elements = self.menu.root.find_node("Response Entry List").get_content()

    def open_menu(self, resource=None):
        self.set_resource(resource)

    def set_resource(self, resource):
      self.response = None
      self.resource = resource
      if self.resource['output'] and self.resource['output variables']:
        self.response = self.resource['output']
        self.show_hierarchy()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)
      else:
        self.setup_variable_config()

    def get_response(self):
      response, _ = self.plugin.make_request.get_response(self.resource, [self.settings.variables])
      self.response = response.text

    def show_hierarchy(self, button=None):
      if not self.response:
        self.get_response()

      self.response_setup.enabled = False
      self.plugin.update_menu(self.response_setup)

      try:
        self.draw_elements(json.loads(self.response))
        self.plugin.update_menu(self.menu)
      except:
        self.__plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Could not parse result as JSON")

    def draw_elements(self, obj, path=[]):
      if type(obj) is dict:
        for key, value in obj.items():
          self.create_button(key, path) 
          self.draw_elements(value, path+[key])
      elif type(obj) is list:
        for i, value in obj:
          self.create_button(str(i), path)
          self.draw_elements(value, path+[str(i)])
      else:
        self.create_button(str(obj), path)

    def create_button(self, text, json_path=None):
      print('drawing button for', text, 'at path', json_path)
      ln = nanome.ui.LayoutNode()
      ln.set_padding(left=(len(json_path))*0.1)
      btn = ln.add_new_button(text)
      btn.name = text
      btn.json_path = json_path
      btn.text.horizontal_align = btn.HorizAlignOptions.Middle
      btn.register_pressed_callback(self.open_variable_setup)
      self.lst_response_elements.items.append(ln)

    def open_variable_setup(self, button):
      self.variable_confirm.var_path = button.json_path

      self.variable_confirm.height = 1
      self.variable_confirm.width = 1
      ln_name = self.variable_confirm.root.create_child_node()
      ln_name.sizing_type = ln_name.SizingTypes.ratio
      ln_name.sizing_value = 0.2

      ln_name.create_child_node().add_new_label('Name').text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle
      ln_var_name = ln_name.create_child_node()
      ln_var_name.forward_dist = 0.02
      inp_var_name = ln_var_name.add_new_text_input()
      inp_var_name.placeholder_text = 'variable name'
      inp_var_name.register_changed_callback(self.set_output_variable)

      ln_selection = self.variable_confirm.root.create_child_node()
      ln_selection.sizing_type = ln_selection.SizingTypes.ratio
      ln_selection.sizing_value = 0.7

      ln_selection.add_new_label(text=button.text.value.idle)

      ln_create_var = self.variable_confirm.root.create_child_node()
      ln_create_var.sizing_type = ln_create_var.SizingTypes.ratio
      ln_create_var.sizing_value = 0.1

      btn_create = ln_create_var.add_new_button(text="Set Resource Variable")
      btn_create.register_pressed_callback(self.create_output_var)

      self.variable_confirm.enabled = True
      self.plugin.update_menu(self.variable_confirm)

      print(f'Are you sure you want to create a variable for {button.name}?')
      print(f'variable path: {button.json_path}')

    def setup_variable_config(self):
      self.response_setup.root.clear_children()
      ln = self.response_setup.root.create_child_node()
      ln.sizing_type = ln.SizingTypes.ratio
      ln.sizing_value = 0.9
      ln.forward_dist = 0.002
      ls = ln.add_new_list()
      pfb = nanome.ui.LayoutNode()
      pfb.layout_orientation = pfb.LayoutTypes.horizontal
      pfb.lbl = pfb.create_child_node().add_new_label('Label')
      pfb.inp = pfb.create_child_node().add_new_text_input()
      pfb.inp.placeholder_text = "test value"

      for name, value in self.settings.get_variables(self.resource).items():
        pfb_var = pfb.clone()
        children = pfb_var.get_children()
        lbl, inp = children[0], children[1]
        lbl.get_content().text_value = name
        inp.get_content().input_text = value
        inp.get_content().register_changed_callback(partial(self.var_changed, name))
        ls.items.append(pfb_var)
        pfb_var.forward_dist = 0.02
      if len(ls.items) is 0:
        self.response_setup.root.clear_children()
        self.response_setup.root.create_child_node().add_new_label('(Resource does not require parameters)')
      
      btn = self.response_setup.root.create_child_node().add_new_button('Show Response')
      btn.register_pressed_callback(self.show_hierarchy)
      self.plugin.update_menu(self.response_setup)

    def var_changed(self, var_name, text_input):
      self.settings.set_variable(var_name, text_input.input_text)

    def set_output_variable(self, text_input):
      self.variable_confirm.var_name = text_input.input_text

    def create_output_var(self, button):
      self.settings.set_output(self.resource, self.response, override=False)
      out_var_names = list(self.resource['output variables'].keys())
      if len(out_var_names):
        var_name = out_var_names[0]
        var_path = self.resource['output variables'][var_name]
      else:
        var_name = self.variable_confirm.var_name
        var_path = self.variable_confirm.var_path
      self.settings.set_output_var(self.resource, var_name, var_path)

      print(f"resources[resource_name]: {self.settings.resources[self.resource['name']]}")
      
      # close variable confirm menu
      self.variable_confirm.enabled = False
      self.plugin.update_menu(self.variable_confirm)
      self.plugin.send_notification(nanome.util.enums.NotificationTypes.success, f"Resource set to output {var_name}")
