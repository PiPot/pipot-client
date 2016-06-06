import hashlib
import hmac
import json
import random
from abc import ABCMeta, abstractmethod

import threading
from time import strftime, gmtime

from twisted.internet import protocol

from pipot.encryption import Encryption


class ICollector:
    """
    Interface that represents a uniform collector.
    """
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def process_data(self, data):
        """
        Server-side processing of received data.

        :param data: A JSONified version of the data.
        :type data: str
        :return: None
        :rtype: None
        """
        pass

    @abstractmethod
    def queue_data(self, service_name, data):
        """
        Client-side processing of data to send

        :param service_name: The name of the service.
        :type service_name: str
        :param data: A JSON collection of data
        :type data: dict
        :return: None
        :rtype: None
        """
        pass


class ClientCollector(ICollector):
    """
    Interface for submitting (sending) a message to the collector
    """

    __metaclass__ = ABCMeta

    """:type : threading.Lock"""
    _collector_lock = threading.Lock()

    def __init__(self, config, reactor):
        """
        Creates an instance of the collector. Expects the JSON config,
        an implementation of the CollectorMessage interface, and the
        reactor of Twisted.

        :param config: The JSON config for the collector.
        :type config: dict[str]
        :param reactor: Instance of the Twisted reactor
        :type reactor: twisted.internet.interfaces.IReactorInThreads
        """
        super(ClientCollector, self).__init__()
        self._config = config
        self._queue = []
        self._reactor = reactor
        self._closing = False
        self._closing_done = False
        # Start queue sender
        reactor.callInThread(self._queue_monitor, random.randint(2, 10))

    def halt_and_catch_fire(self):
        """
        Sends a final message and flushes the queue.

        :return: None
        :rtype: None
        """
        self.queue_data('PiPot', 'PiPot shutting down')
        self._closing = True
        while not self._closing_done:
            import time
            time.sleep(1)

    def process_data(self, data):
        pass

    def queue_data(self, service_name, data):
        """
        Adds a message from a given service to the queue, so it can be sent
        at a random time interval.

        :param service_name: The name of the service calling the method.
        :type service_name: str
        :param data: The message (can be an object too). Must be JSON
            serializable.
        :type data: Any
        :return: None
        :rtype: None
        """
        with self._collector_lock:
            self._queue.append({
                'service': service_name,
                'data': data,
                'timestamp': strftime("%Y-%m-%d %H:%M:%S", gmtime())
            })

    def _queue_monitor(self, max_queue_length):
        """
        Monitors the queue, and calls the submit_message of the collector
        if either a certain time elapses, or if the queue length exceeds
        the provided max_queue_length.

        :param max_queue_length: The maximum amount of entries that the
        queue should hold before sending them at once.
        :type max_queue_length: int
        :return: None
        :rtype: None
        """
        import time
        print('Waiting until we collected %s items or are 5 minutes away '
              'from now' % max_queue_length)
        timeout = time.time() + 60*5   # 5 minutes from now
        while len(self._queue) < max_queue_length and time.time() < timeout\
                and not self._closing:
            time.sleep(1)
        if len(self._queue) > 0:
            print('Sending queued messages')
            queue = []
            with self._collector_lock:
                queue.extend(self._queue)
                self._queue = []
            self._submit_messages(queue)
        if not self._closing:
            print('Restarting queue_monitor')
            self._reactor.callInThread(
                self._queue_monitor,
                random.randint(2, 10)
            )
        else:
            self._closing_done = True

    @abstractmethod
    def _submit_messages(self, queue):
        pass

    def _encode_message(self, data):
        """
        Converts the given data into a JSON encoded string for transmission
        to the collector.

        :param data: The messages to send. Must be JSON serializable.
        :type data: Any
        :return: A JSON-encoded string.
        :rtype: str
        """
        # Calculate MAC over content
        mac = hmac.new(
            str(self._config['mac_key']),
            str(json.dumps(data, sort_keys=True)),
            hashlib.sha256
        ).hexdigest()
        # Return JSON of the auth_key & the encrypted messages
        encrypted = Encryption.encrypt(
            self._config['encryption_key'],
            json.dumps({'hmac': mac, 'content': data})
        )
        return json.dumps({
            'instance': self._config['instance_key'],
            'data': encrypted
        })


class ClientCollectorUDPProtocol(protocol.DatagramProtocol, ClientCollector):
    """
    Class that implements both the DatagramProtocol from Twisted and the
    CollectorMessage class, so it can send the messages to the collector
    through UDP.
    """

    def __init__(self, config, reactor):
        """
        Initializes the instance of this UDP protocol. Requires a host &
        port to connect to.

        :param config: The JSON config for the collector.
        :type config: dict[str]
        :param reactor: Instance of the Twisted reactor
        :type reactor: twisted.internet.interfaces.IReactorInThreads
        """
        super(ClientCollectorUDPProtocol, self).__init__(
            config=config, reactor=reactor)
        self._udp_queue = []

    def startProtocol(self):
        self.transport.connect(self._config['host'], self._config['port'])
        if len(self._udp_queue) > 0:
            print("Sending queued UDP messages")
            for message in self._udp_queue:
                self.transport.write(self._encode_message(message))
                self._udp_queue.remove(message)

    def _submit_messages(self, queue):
        # Need to check. Might not be initialized yet...
        if self.transport is None:
            print("UDP Transport is not initialized! Queueing message")
            self._udp_queue.append(queue)
            return
        print("Sending message through UDP")
        self.transport.write(self._encode_message(queue))


class CollectorSSLProtocol(protocol.Protocol):
    """
    Simple TCP protocol for connecting to a collector through a TCP
    connection
    """
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        self.factory._collectors.append(self)

    def connectionLost(self, reason=protocol.connectionDone):
        self.factory._collectors.remove(self)


class ClientCollectorSSLFactory(protocol.ClientFactory, ClientCollector):
    """
    TCP factory that implements the default ClientFactory, as well as the
    CollectorMessage interface, so messages can be sent through TCP (SSL)
    """

    """:type : list[protocol.Protocol]"""
    _collectors = []

    def __init__(self, config, reactor):
        """
        :param config: The JSON config for the collector.
        :type config: dict[str]
        :param reactor: Instance of the Twisted reactor
        :type reactor: twisted.internet.interfaces.IReactorInThreads
        """
        super(ClientCollectorSSLFactory, self).__init__(
            config=config, reactor=reactor)

    def buildProtocol(self, addr):
        return CollectorSSLProtocol(self)

    def _submit_messages(self, queue):
        for collector in self._collectors:
            collector.transport.write(self._encode_message(queue))
