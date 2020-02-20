import os
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement, ResourceDisplayType
from ..menus import ResourceConfigurationMenu
MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "Resources.json")

class ResourcesMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.resource_config = ResourceConfigurationMenu(plugin, settings)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 3

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
        if self.settings.rename_resource(resource, new_name):
            self.plugin.requests.config.refresh_steps()
            if resource['references'].get(self.plugin.make_request.request.get('id')):
                self.plugin.make_request.show_request()
            return True
        return False

    def change_resource(self, resource, new_url):
        if self.settings.change_resource(resource, new_url=new_url):
            if resource['references'].get(self.plugin.make_request.request.get('id')):
                self.plugin.make_request.show_request()
            return True
        return False

    def add_resource(self, method, button = None):
        name = f'Resource {len(self.settings.resource_ids)+1}'
        resource = self.settings.add_resource(name, '', method)
        delete = partial(self.delete_resource, resource)
        open_config = partial(self.resource_config.open_menu, resource)
        el = ListElement(
            self.plugin,
            self.lst_resources,
            name,
            '',
            self.settings.resources,
            ResourceDisplayType.Mutable,
            False,
            self.resource_config,
            deleted=delete,
            renamed=partial(self.rename_resource, resource),
            reresourced=partial(self.change_resource, resource),
            config_opened=open_config
        )
        self.lst_resources.items.append(el)
        self.plugin.update_content(self.lst_resources)

    def refresh_resources(self):
        self.lst_resources.items = []
        for r_id, resource in self.settings.resources.items():
            name = resource['name']
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
                reresourced=partial(self.change_resource, resource),
                config_opened=partial(self.resource_config.open_menu, resource)
            )
            self.lst_resources.items.append(el)