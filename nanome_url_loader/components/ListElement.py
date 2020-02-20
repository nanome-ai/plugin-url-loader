import os
import re
from functools import partial
from enum import IntEnum

import nanome

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
JSON_PATH = os.path.join(BASE_PATH, 'json', 'ListElement2.json')

IMG_RENAME_PATH = os.path.join(BASE_PATH, '..', 'icons', 'rename.png')
IMG_CONFIG_PATH = os.path.join(BASE_PATH, '..', 'icons', 'config.png')
IMG_CHECK_PATH = os.path.join(BASE_PATH, '..', 'icons', 'check.png')
IMG_UNCHECK_PATH = os.path.join(BASE_PATH, '..', 'icons', 'uncheck.png')

class ResourceDisplayType(IntEnum):
    Fixed = 0
    Selectable = 1
    Mutable = 2

class ListElement(nanome.ui.LayoutNode):
    def __init__(self, plugin, ui_list, name, resource_value = None, resource_source = None, resource_display_type = ResourceDisplayType.Fixed, externally_used = False, config = None, deleted = None, renamed = None, reresourced = None, external_toggle = None, config_opened = None, config_closed = None):
        nanome.ui.LayoutNode.__init__(self, name)
        ln = nanome.ui.LayoutNode.io.from_json(JSON_PATH)
        self.add_child(ln)

        self.config = config
        self.plugin = plugin
        self.ui_list = ui_list

        self.resource_value = resource_value
        self.resource_display_type = resource_display_type
        self.resource_source = resource_source

        self.deleted = deleted
        self.renamed = renamed
        self.reresourced = reresourced
        self.external_toggle = external_toggle
        self.config_opened = config_opened
        self.config_closed = config_closed

        self.btn_delete = ln.find_node("Delete").get_content()
        self.btn_delete.register_pressed_callback(self.remove_from_list)

        self.ln_top = ln.find_node("Top Panel")
        self.ln_static_label = ln.find_node("Static Resource Label")
        self.lbl_resource = ln.find_node("Resource Label").get_content()

        self.ln_name   = ln.find_node("Name")
        self.ln_name.add_new_label(name).text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle

        self.ln_rename = ln.find_node("Rename")
        self.ln_rename.find_node("Image").add_new_image(IMG_RENAME_PATH)
        self.ln_rename.get_content().register_pressed_callback(self.toggle_rename)

        self.ln_resource = ln.find_node("Resource")
        self.ln_resource.add_new_label(resource_value or '').text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle

        self.ln_use_externally    = ln.find_node("Use Externally")
        self.ln_use_externally.find_node("Image").add_new_image(IMG_UNCHECK_PATH)
        self.ln_use_externally.get_content().register_pressed_callback(self.toggle_use_externally)

        self.set_tooltip("Override resource data in request")

        self.ln_config = ln.find_node("Config")
        self.ln_config.find_node("Image").add_new_image(IMG_CONFIG_PATH)
        self.ln_config.get_content().register_pressed_callback(self.open_config)

        self.configure_for_resource_type(resource_display_type)
        self.set_externally_usable(externally_used)
        self.set_top_panel_text('')

    def set_list(self, ui_list):
        self.ui_list = ui_list

    def remove_from_list(self, button=None):
        if self.ui_list:
            if self.deleted and self.deleted(self):
                items = self.ui_list.items
                del self.ui_list.items[items.index(self)]
                self.plugin.update_content(self.ui_list)

    def toggle_rename(self, button):
        button.selected = not button.selected
        self.ln_rename.find_node("Image").add_new_image(IMG_CHECK_PATH if button.selected else IMG_RENAME_PATH)
        if button.selected:
            name = self.ln_name.get_content().text_value
            text_input = self.ln_name.add_new_text_input()
            text_input.max_length = 16
            text_input.input_text = name
            text_input.placeholder_text = "Name"
            text_input.register_submitted_callback(lambda inp: self.toggle_rename(button))
        else:
            text_input = self.ln_name.get_content()
            self.clean_input(text_input)
            if not text_input.input_text:
                button.selected = not button.selected
                return
            if self.renamed and self.renamed(self, text_input.input_text):
                self.name = text_input.input_text
                self.ln_name.add_new_label(self.name).text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle
        self.plugin.update_content(self.ui_list)

    def configure_for_resource_type(self, new_display_type, source=None):
        if self.resource_value is None:
            self.set_resource_visible(False)
            return
        if self.resource_source is None:
            self.resource_source = source

        if new_display_type is ResourceDisplayType.Fixed:
            self.ln_resource.add_new_label(self.resource_value).text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle
        elif new_display_type is ResourceDisplayType.Selectable:
            ls_resources = self.ln_resource.add_new_list()
            for name, resource in self.resource_source.items():
                ln_rsrc = nanome.ui.LayoutNode()
                btn = ln_rsrc.add_new_button(name)
                btn.register_pressed_callback(self.select_resource)
                ls_resources.items.append(ln_rsrc)
        elif new_display_type is ResourceDisplayType.Mutable:
            text_input = self.ln_resource.add_new_text_input()
            text_input.max_length = 0
            text_input.input_text = self.resource_value
            text_input.placeholder_text = "resource.url/{{request_field}}"
            text_input.register_changed_callback(self.reresourced_from_input)
            text_input.register_submitted_callback(self.reresourced_from_input)

    def reresourced_from_input(self, text_input):
        self.resource_value = text_input.input_text
        self.reresourced(text_input.input_text)

    def select_resource(self, button):
        for ln in self.ln_resource.get_content().items:
            a_btn = ln.get_content()
            a_btn.selected = a_btn is button
        self.resource_value = button.text_value
        self.plugin.update_node(self.ln_resource)

    def set_resource_value(self, text_input):
        self.resource_value = text_input.input_text

    def set_resource_placeholder(self, placeholder_text):
        if self.resource_display_type is ResourceDisplayType.Mutable:
            self.ln_resource.get_content().placeholder_text = placeholder_text
        self.plugin.update_node(self.ln_resource)

    def set_resource_display(self, display_text):
        if self.resource_display_type is ResourceDisplayType.Mutable:
            self.ln_resource.get_content().input_text = display_text
        self.resource_value = display_text
        self.plugin.update_node(self.ln_resource)

    def set_top_panel_text(self, text):
        self.lbl_resource.text_value = text
        self.ln_static_label.enabled = not not text
        if not text:
            self.ln_top.remove_content()
        else:
            self.ln_top.add_new_mesh().mesh_color = nanome.util.color.Color(0, 0, 50)
        self.plugin.update_content(self.ui_list)

    def set_resource_visible(self, visible):
        self.ln_resource.enabled = visible
        self.plugin.update_node(self.ln_resource)

    def set_use_externally(self, use, update=True):
        self.ln_use_externally.find_node("Image").add_new_image(IMG_CHECK_PATH if use else IMG_UNCHECK_PATH)
        self.ln_use_externally.get_content().selected = use
        if update: self.plugin.update_content(self.ui_list)

    def toggle_use_externally(self, button):
        if self.external_toggle and self.external_toggle(self, not button.selected):
            self.set_use_externally(not button.selected)

    def set_externally_usable(self, used=True, update=True):
        self.ln_use_externally.enabled = used
        self.plugin.update_node(self.ln_use_externally)

    def set_tooltip(self, text):
        button = self.ln_use_externally.get_content()
        button.tooltip.title = text
        button.tooltip.positioning_target = button.ToolTipPositioning.bottom
        button.tooltip.positioning_origin = button.ToolTipPositioning.top
        # button.tooltip.bounds.y = 0.25

    def clean_input(self, text_input):
        text_input.input_text = re.sub("[^0-9A-z-._~:/\{\} ]", '', text_input.input_text)

    def open_config(self, button):
        if self.config_opened:
            self.config_opened()
