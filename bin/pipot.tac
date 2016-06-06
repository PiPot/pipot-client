import traceback

from twisted.application import service, internet as t_a_i
from twisted.internet import reactor, ssl

import clientCollector
import config
from pipot.services import ServiceLoader, IService

application = service.Application("pipotd")
collector_config = config.config_inst.get_collector_config()
if not config.is_valid_collector_config(collector_config):
    raise ValueError('Collector config is incomplete')

if collector_config['protocol'] == 'udp':
    collector_inst = clientCollector.ClientCollectorUDPProtocol(
        collector_config, reactor)
    collector_connection = t_a_i.UDPServer(
        collector_config['port'],
        collector_inst
    )
else:
    collector_inst = clientCollector.ClientCollectorSSLFactory(
        collector_config, reactor)
    collector_connection = t_a_i.SSLClient(
        collector_config['host'],
        collector_config['port'],
        collector_inst,
        ssl.ClientContextFactory()
    )
collector_connection.setServiceParent(application)

# List of modules to start
services_to_enable = config.config_inst.get_services()

for service in services_to_enable:
    class_name = service['name']
    try:
        instance = ServiceLoader.get_class_instance(
            service['name'], collector_inst, service['config'])
        if isinstance(instance, IService.INetworkService):
            service = instance.get_service()
            service.setServiceParent(application)
            collector_inst.queue_data(
                'PiPot', '%s (NetworkService) started' % class_name)
        elif isinstance(instance, IService.ISystemService):
            instance.run()
            # Add before shutdown trigger to close service(s) started by
            # this service.
            reactor.addSystemEventTrigger('before', 'shutdown', instance.stop)
            collector_inst.queue_data(
                'PiPot', '%s (SystemService) started' % class_name)
        else:
            collector_inst.queue_data(
                'PiPot', '%s is not a valid service' % class_name)
    except Exception as e:
        error_message = 'Failed to boot the %s service: %s' % (
            class_name, traceback.format_exc())
        collector_inst.queue_data('PiPot', error_message)

# Make sure that before shutdown all remaining messages are sent
reactor.addSystemEventTrigger('before', 'shutdown',
                              collector_inst.halt_and_catch_fire)

collector_inst.queue_data('PiPot', 'PiPot booted')
