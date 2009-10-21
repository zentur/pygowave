import os
import sys

from twisted.application import service, internet
from twisted.words.protocols.jabber import component

import settings
from component.wavefederationservice import WaveFederationService
from component.logservice import LogService

# includes for txamqp
from twisted.internet import reactor, protocol
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.protocol import ClientCreator
from txamqp.protocol import AMQClient
from txamqp.client import TwistedDelegate
import txamqp.spec

# add permission for pygowave_server to the federation queue
# rabbitmqctl add_user pygowave_xmpp pygowave_xmpp 
# rabbitmqctl set_permissions pygowave_xmpp '^[^.]+\.[^.]+\.waveop$|^federation$|^wavelet\.(topic|direct)$' '^[^.]+\.[^.]+\.waveop$|^federation$|^wavelet\.direct$' '^[^.]+\.[^.]+\.waveop$|^federation$|^wavelet\.(topic|direct)$'

application = service.Application("pygowave-federation")

# set up Jabber Component
sm = component.buildServiceManager(settings.JABBERID, settings.JABBER_PASSWORD, ("tcp:127.0.0.1:5275" ))

# Turn on verbose mode
LogService().setServiceParent(sm)

# set up our Service
fed = WaveFederationService()
fed.setServiceParent(sm)


sm.setServiceParent(application)

def error(err):
    print err

class AMQPConnector():
    def __init__(self, host, port, vhost, username, password, spec, fed):
        self.hostname = host
        self.port = port
        self.vhost = vhost
        self.username = username
        self.password = password
        self.spec = txamqp.spec.load(spec)
        self.fed = fed

#    @inlineCallbacks
    def connect(self, application):
        delegate = TwistedDelegate()
        onConn = Deferred()
        onConn.addCallback(self.gotAMQPConnection)
        onConn.addErrback(error)
        f = protocol._InstanceFactory(reactor, AMQClient(delegate, self.vhost, self.spec), onConn)

        internet.TCPClient(self.hostname, self.port, f).setServiceParent(application)
        

    @inlineCallbacks
    def gotAMQPConnection(self, conn):
        print "Connected to broker."
        yield conn.authenticate(self.username, self.password)

        print "Authenticated. Ready to receive messages"
        chan = yield conn.channel(1)
        yield chan.channel_open()

        yield chan.queue_declare(queue="federation", durable=True, exclusive=False, auto_delete=False)
        #yield chan.exchange_declare(exchange="wavelet.topic", type="direct", durable=True, auto_delete=False)

        yield chan.queue_bind(queue="federation", exchange="wavelet.topic", routing_key="#.#.clientop")

        yield chan.basic_consume(queue='federation', no_ack=True, consumer_tag="testtag")

        queue = yield conn.queue("testtag")

        while True:
            msg = yield queue.get()
            yield self.fed.processAMQPMessage(msg, chan)

        yield chan.basic_cancel("testtag")
        yield chan.channel_close()
        chan0 = yield conn.channel(0)
        yield chan0.connection_close()


hostname = 'localhost'
port = 5672
vhost = '/'
username = 'pygowave_xmpp'
password = 'pygowave_xmpp'
spec = 'amqp0-8.xml'

con = AMQPConnector(hostname, port, vhost, username, password, spec, fed)
con.connect(application)


