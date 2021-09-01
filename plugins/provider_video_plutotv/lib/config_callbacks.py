
from .channels import Channels
from lib.plugins.plugin_handler import PluginHandler

def force_channelsdb_refresh(_config_obj, _section, _key):
    locast_obj = PluginHandler.cls_plugins['Locast'].plugin_obj
    instance = _section.split('_', 1)[1]
    locast_obj.instances[instance].channels.refresh_channels(True)


