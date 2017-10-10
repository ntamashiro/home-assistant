"""
Support for switch controlled using a telnet connection.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.telnet/
"""
import logging
import telnetlib
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA,
                                             ENTITY_ID_FORMAT)
from homeassistant.const import (
    CONF_RESOURCE, CONF_NAME, CONF_SWITCHES, CONF_VALUE_TEMPLATE,
    CONF_COMMAND_OFF, CONF_COMMAND_ON, CONF_COMMAND_STATE, CONF_PORT)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 23

SWITCH_SCHEMA = vol.Schema({
    vol.Required(CONF_COMMAND_ON):
    cv.string,
    vol.Required(CONF_COMMAND_OFF):
    cv.string,
    vol.Optional(CONF_COMMAND_STATE):
    cv.string,
    vol.Optional(CONF_NAME):
    cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT):
    cv.port,
    vol.Required(CONF_RESOURCE):
    cv.string,
    vol.Required(CONF_VALUE_TEMPLATE):
    cv.template,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SWITCHES):
    vol.Schema({
        cv.slug: SWITCH_SCHEMA
    }),
})

SCAN_INTERVAL = timedelta(seconds=10)


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Find and return switches controlled by telnet commands."""
    devices = config.get(CONF_SWITCHES, {})
    switches = []

    for object_id, device_config in devices.items():
        value_template = device_config.get(CONF_VALUE_TEMPLATE)

        if value_template is not None:
            value_template.hass = hass

        switches.append(
            TelnetSwitch(hass, object_id,
                         device_config.get(CONF_RESOURCE),
                         device_config.get(CONF_PORT),
                         device_config.get(CONF_NAME, object_id),
                         device_config.get(CONF_COMMAND_ON),
                         device_config.get(CONF_COMMAND_OFF),
                         device_config.get(CONF_COMMAND_STATE),
                         value_template))

    if not switches:
        _LOGGER.error("No switches added")
        return False

    add_devices(switches)


class TelnetSwitch(SwitchDevice):
    """Representation of a switch that can be toggled using telnet commands."""

    def __init__(self, hass, object_id, resource, port, friendly_name,
                 command_on, command_off, command_state, value_template):
        """Initialize the switch."""
        self._hass = hass
        self.entity_id = ENTITY_ID_FORMAT.format(object_id)
        self._resource = resource
        self._port = port
        self._name = friendly_name
        self._state = False
        self._command_on = command_on
        self._command_off = command_off
        self._command_state = command_state
        self._value_template = value_template

    def _telnet_command(self, command):
        try:
            telnet = telnetlib.Telnet(self._resource, self._port)
            telnet.write(command.encode('ASCII') + b'\r')
            response = telnet.read_until(b'\r', timeout=0.2)
            return response.decode('ASCII').strip()
        except IOError as error:
            _LOGGER.error('Command "%s" failed with exception: %s', command,
                          repr(error))
            return None

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def should_poll(self):
        """Only poll if we have state command."""
        return self._command_state is not None

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def assumed_state(self):
        """Default ist true if no state command is defined, false otherwise."""
        return self._command_state is None

    def update(self):
        """Update device state."""
        response = self._telnet_command(self._command_state)
        if response:
            rendered = self._value_template \
                .render_with_possible_json_value(response)
            self._state = rendered == "True"
        else:
            _LOGGER.warning("Empty response for command: %s",
                            self._command_state)

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._telnet_command(self._command_on)
        if self.assumed_state:
            self._state = True

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._telnet_command(self._command_off)
        if self.assumed_state:
            self._state = False
