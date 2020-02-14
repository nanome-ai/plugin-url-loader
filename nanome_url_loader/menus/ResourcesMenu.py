import os
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement, ResourceDisplayType
from .ResourceConfigurationMenu import ResourceConfigurationMenu
MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "Resources.json")

class ResourcesMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.resource_config = ResourceConfigurationMenu(plugin, settings)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 3

        self.rsrc_i = 0

        self.lst_resources = self.menu.root.find_node('Resources List').get_content()
        self.add_get_resource = self.menu.root.find_node('Add Get Resource').get_content()
        self.add_get_resource.register_pressed_callback(partial(self.add_resource, 'get'))
        self.add_post_resource = self.menu.root.find_node('Add Post Resource').get_content()
        self.add_post_resource.register_pressed_callback(partial(self.add_resource, 'post'))


    def open_menu(self):
        self.refresh_resources()
        self.menu.enabled = True
        self.plugin.update_menu(self.menu)

    def delete_resource(self, resource, list_element):
        return self.settings.delete_resource(resource)

    def rename_resource(self, resource, element, new_name):
        return self.settings.rename_resource(resource, new_name)

    def change_resource_url(self, resource, new_url):
        if self.settings.change_resource_url(resource, new_url):
            if resource['references'].get(self.plugin.request['name']):
                self.plugin.show_request()
            return True
        return False

    def add_resource(self, method, button = None):
        name = f'Resource {self.rsrc_i}'
        value = f'resource{self.rsrc_i}.url/'+'{RequestParameter}'
        resource = self.settings.add_resource(name, value, method)
        self.rsrc_i += 1
        delete = partial(self.delete_resource, resource)
        open_config = partial(self.resource_config.open_menu, resource)
        el = ListElement(
            self.plugin,
            self.lst_resources,
            name,
            value,
            self.settings.resources,
            ResourceDisplayType.Mutable,
            False,
            self.resource_config,
            deleted=delete,
            renamed=partial(self.rename_resource, resource),
            reresourced=partial(self.change_resource_url, resource),
            config_opened=open_config
        )
        self.lst_resources.items.append(el)
        self.plugin.update_content(self.lst_resources)

    def refresh_resources(self):
        self.lst_resources.items = []
        for name, resource in self.settings.resources.items():
            self.rsrc_i += 1
            el = ListElement(
                self.plugin,
                self.lst_resources,
                name,
                resource['url'],
                None,
                ResourceDisplayType.Mutable,
                False,
                self.resource_config,
                deleted=partial(self.delete_resource, resource),
                renamed=partial(self.rename_resource, resource),
                reresourced=partial(self.change_resource_url, resource),
                config_opened=partial(self.resource_config.open_menu, resource)
            )
            self.lst_resources.items.append(el)