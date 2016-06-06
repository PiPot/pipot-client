import json
from pkg_resources import resource_filename


class Config:
    """
    Class that holds the general config for this honeypot instance. Loads
    the honeypot_profile.json upon init.
    """

    """ :type : dict"""
    _config = None

    def __init__(self):
        cfg_file = resource_filename(__name__, 'honeypot_profile.json')
        try:
            with open(cfg_file, "r") as f:
                print("[-] Loading config file")
                self._config = json.load(f)
            return
        except IOError as e:
            print("[-] Could not open config file: %s" % e)
        except ValueError as e:
            print("[-] Could not decode json from config: (%s)" % e)
        except Exception as e:
            print("[-] An unexpected error occurred loading the config (%s)"
                  % e)

    def service_enabled(self, module_name):
        """
        Checks if a given service (by it's module name) is enabled or not.

        :param module_name: The module name to check.
        :type module_name: str
        :return: Is the module in the config and set as enabled?
        :rtype: bool
        """
        k = "%s.enabled" % module_name.lower()
        if k in self._config:
            return bool(self._config[k])
        return False

    def get_services(self):
        """
        Returns a list of services that are enabled, or an empty list.

        :return: A list of services that are enabled, with the config.
        :rtype: list[dict[str]]
        """
        services = []
        if 'services' in self._config:
            services = self._config['services']
        return services

    def get_collector_config(self):
        """
        Returns the collector config, or an empty dict.

        :return: The collector config, or an empty dict.
        :rtype: dict
        """
        collector_config = {}
        if 'collector' in self._config:
            collector_config = self._config['collector']
        return collector_config

    def __repr__(self):
        # Just return the __repr__ of the config value.
        return self._config.__repr__()

    def __str__(self):
        # Just return the __repr__ of the config value.
        return self._config.__str__()

    def to_dict(self):
        """
        Return all settings as a dict.

        :return: The settings as a dict.
        :rtype: dict
        """
        return self._config

    def to_json(self):
        """
        gets a JSON representation of config.

        :return: JSON string representation of config.
        :rtype: str
        """
        return json.dumps(self._config, sort_keys=True, indent=4,
                          separators=(',', ': '))


def is_valid_collector_config(c):
    """
    Checks if all necessary values are present for the collector config to
    work.

    :param c: Collector config
    :type c: dict
    :return: Is the given config valid for a collector
    :rtype: bool
    """
    return isinstance(c, dict) and 'instance_key' in c and 'mac_key' in c \
        and 'encryption_key' in c and 'port' in c and 'host' in c and \
        'protocol' in c

config_inst = Config()
