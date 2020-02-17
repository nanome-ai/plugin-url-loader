import os
from functools import partial

import nanome
from nanome.util import Logs

from ..components import ListElement, ResourceDisplayType
from ..menus import ResourceConfigurationMenu

MENU_PATH = os.path.join(os.path.dirname(__file__), "json", "RequestConfig.json")

class RequestConfigurationMenu():
    def __init__(self, plugin, settings):
        self.plugin = plugin
        self.settings = settings
        self.resource_config = ResourceConfigurationMenu(plugin, settings)
        self.menu = nanome.ui.Menu.io.from_json(MENU_PATH)
        self.menu.index = 2

        self.request = None
        self.resource = None

        self.step_i = 1

        self.lst_steps = self.menu.root.find_node('Step List').get_content()
        self.lst_all_steps = self.menu.root.find_node('All Steps List').get_content()
        self.btn_add_step = self.menu.root.find_node('Add Step').get_content()
        self.btn_add_step.register_pressed_callback(self.add_step)

    def open_menu(self, request):
        self.menu.enabled = True
        self.refresh_resources()
        self.set_request(request)
        self.plugin.update_menu(self.menu)

    def refresh_resources(self):
        self.lst_all_steps.items = []
        if not self.resource and self.settings.resources:
            print(f'{self.settings.resources}')
            print(f'{self.settings.resource_names}')
            self.resource = self.settings.resources[self.settings.resource_names[-1]]
        for name, resource in self.settings.resources.items():
            pfb = nanome.ui.LayoutNode()
            btn = pfb.add_new_button(name)
            btn.resource = resource
            btn.selected = name == self.resource['name']
            btn.text_horizontal_align = nanome.util.enums.HorizAlignOptions.Middle
            btn.register_pressed_callback(self.set_resource)
            self.lst_all_steps.items.append(pfb)
        self.plugin.update_content(self.lst_all_steps)

    def set_resource(self, button):
        self.resource = button.resource
        for element in self.lst_all_steps.items:
            btn = element.get_content()
            btn.selected = btn.resource['name'] == self.resource['name']
        self.plugin.update_content(self.lst_all_steps)

    def set_request(self, request):
        self.request = request
        self.lst_steps.items = []
        steps = request['steps']
        self.step_i = len(steps) + 1
        for step in steps:
            step_name = step['name']
            resource = step['resource']
            external_toggle = partial(self.toggle_use_data_in_request, step)
            open_config = partial(self.config_opened, resource)
            el = ListElement(
                self.plugin,
                self.lst_steps,
                step_name,
                '',
                self.settings.resources,
                ResourceDisplayType.Mutable,
                resource['method'] == 'post',
                self.menu,
                deleted=self.delete_step,
                renamed=partial(self.rename_step, step),
                reresourced=partial(self.validate_new_resource, step),
                external_toggle=external_toggle,
                config_opened=open_config
            )
            el.set_top_panel_text(resource['name'])
            el.set_resource_placeholder("Metadata source ({{step1}})")
            el.set_tooltip('Override post data during request')
            self.lst_steps.items.append(el)

    def add_step(self, button):
        step_name = f'Step {self.step_i}'
        self.step_i += 1
        if not len(self.settings.resource_names):
            self.settings.create_empty_resource()
        resource_name = self.resource['name'] if self.resource else self.settings.resource_names[-1]
        step = self.settings.add_step(self.request['name'], step_name, resource_name, '', False)
        if not step:
            return
        external_toggle = partial(self.toggle_use_data_in_request, step)
        open_config = partial(self.config_opened, self.settings.resources[resource_name])
        close_config = partial(self.config_closed, self.settings.resources[resource_name])
        el = ListElement(
            self.plugin,
            self.lst_steps,
            step_name,
            '',
            self.settings.resources,
            ResourceDisplayType.Mutable,
            self.resource['method'] == 'post',
            self.menu,
            deleted=self.delete_step,
            renamed=partial(self.rename_step, step),
            reresourced=partial(self.validate_new_resource, step),
            external_toggle=external_toggle,
            config_opened=open_config,
            config_closed=close_config
        )
        el.set_top_panel_text(resource_name)
        el.set_resource_placeholder('Metadata source ({{step1}})')
        el.set_tooltip('Override post data during request')
        self.lst_steps.items.append(el)
        self.plugin.update_content(self.lst_steps)

    def delete_step(self, element):
        index = self.lst_steps.items.index(element)
        return self.settings.delete_step(self.request['name'], index)

    def rename_step(self, step, element, new_name):
        return self.settings.rename_step(self.request['name'], step, new_name)

    def validate_new_resource(self, step, metadata_source_name):
        step_index = self.plugin.make_request.request['steps'].index(step)
        if metadata_source_name in self.settings.variables:
            step['metadata_source'] = metadata_source_name
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.success, "Resource for step updated")
            return True
        else:
            self.plugin.send_notification(nanome.util.enums.NotificationTypes.error, "Resource does not exist")
            return False

    def config_opened(self, resource):
        self.resource_config.open_menu(resource)
        # request = self.settings.requests[self.request]
        # first = True
        # for ln_element in self.lst_steps.items:
        #     if step['resource'] is resource:
        #         self.resource_config.add_step_dependency()
        #     first = False
        # return True

    def config_closed(self, resource):
        pass

    def toggle_use_data_in_request(self, step, element, use_data):
        step['override_data'] = not step['override_data']
        self.plugin.make_request.show_request()
        return True

    def refresh_steps(self):
        self.set_request(self.request)
        self.plugin.update_content(self.lst_steps)