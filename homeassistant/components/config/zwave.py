"""Provide configuration end points for Z-Wave."""
import asyncio

import homeassistant.core as ha
from homeassistant.const import HTTP_NOT_FOUND
from homeassistant.components.http import HomeAssistantView
from homeassistant.components.config import EditKeyBasedConfigView
from homeassistant.components.zwave import const, DEVICE_CONFIG_SCHEMA_ENTRY
import homeassistant.helpers.config_validation as cv

CONFIG_PATH = 'zwave_device_config.yaml'
OZW_LOG_FILENAME = 'OZW_Log.txt'
URL_API_OZW_LOG = '/api/zwave/ozwlog'


@asyncio.coroutine
def async_setup(hass):
    """Set up the Z-Wave config API."""
    hass.http.register_view(
        EditKeyBasedConfigView('zwave', 'device_config', CONFIG_PATH,
                               cv.entity_id, DEVICE_CONFIG_SCHEMA_ENTRY))
    hass.http.register_view(ZWaveNodeValueView)
    hass.http.register_view(ZWaveNodeGroupView)
    hass.http.register_view(ZWaveNodeConfigView)
    hass.http.register_view(ZWaveUserCodeView)
    hass.http.register_static_path(URL_API_OZW_LOG,
                                   hass.config.path(OZW_LOG_FILENAME), False)

    return True


class ZWaveNodeValueView(HomeAssistantView):
    """View to return the node values."""

    url = r"/api/zwave/values/{node_id:\d+}"
    name = "api:zwave:values"

    @ha.callback
    def get(self, request, node_id):
        """Retrieve groups of node."""
        nodeid = int(node_id)
        hass = request.app['hass']
        values_list = hass.data[const.DATA_ENTITY_VALUES]

        values_data = {}
        # Return a list of values for this node that are used as a
        # primary value for an entity
        for entity_values in values_list:
            if entity_values.primary.node.node_id != nodeid:
                continue

            values_data[entity_values.primary.value_id] = {
                'label': entity_values.primary.label,
                'index': entity_values.primary.index,
                'instance': entity_values.primary.instance,
                'poll_intensity': entity_values.primary.poll_intensity,
            }
        return self.json(values_data)


class ZWaveNodeGroupView(HomeAssistantView):
    """View to return the nodes group configuration."""

    url = r"/api/zwave/groups/{node_id:\d+}"
    name = "api:zwave:groups"

    @ha.callback
    def get(self, request, node_id):
        """Retrieve groups of node."""
        nodeid = int(node_id)
        hass = request.app['hass']
        network = hass.data.get(const.DATA_NETWORK)
        node = network.nodes.get(nodeid)
        if node is None:
            return self.json_message('Node not found', HTTP_NOT_FOUND)
        groupdata = node.groups
        groups = {}
        for key, value in groupdata.items():
            groups[key] = {
                'associations': value.associations,
                'association_instances': value.associations_instances,
                'label': value.label,
                'max_associations': value.max_associations
            }
        return self.json(groups)


class ZWaveNodeConfigView(HomeAssistantView):
    """View to return the nodes configuration options."""

    url = r"/api/zwave/config/{node_id:\d+}"
    name = "api:zwave:config"

    @ha.callback
    def get(self, request, node_id):
        """Retrieve configurations of node."""
        nodeid = int(node_id)
        hass = request.app['hass']
        network = hass.data.get(const.DATA_NETWORK)
        node = network.nodes.get(nodeid)
        if node is None:
            return self.json_message('Node not found', HTTP_NOT_FOUND)
        config = {}
        for value in (node.get_values(
                class_id=const.COMMAND_CLASS_CONFIGURATION).values()):
            config[value.index] = {
                'label': value.label,
                'type': value.type,
                'help': value.help,
                'data_items': value.data_items,
                'data': value.data,
                'max': value.max,
                'min': value.min
            }
        return self.json(config)


class ZWaveUserCodeView(HomeAssistantView):
    """View to return the nodes usercode configuration."""

    url = r"/api/zwave/usercodes/{node_id:\d+}"
    name = "api:zwave:usercodes"

    @ha.callback
    def get(self, request, node_id):
        """Retrieve usercodes of node."""
        nodeid = int(node_id)
        hass = request.app['hass']
        network = hass.data.get(const.DATA_NETWORK)
        node = network.nodes.get(nodeid)
        if node is None:
            return self.json_message('Node not found', HTTP_NOT_FOUND)
        usercodes = {}
        if not node.has_command_class(const.COMMAND_CLASS_USER_CODE):
            return self.json(usercodes)
        for value in (node.get_values(class_id=const.COMMAND_CLASS_USER_CODE)
                      .values()):
            if value.genre != const.GENRE_USER:
                continue
            usercodes[value.index] = {
                'code': value.data,
                'label': value.label,
                'length': len(value.data)
            }
        return self.json(usercodes)
