# -*- coding: utf8 -*-
"""

 PyGoWave Server - The Python Google Wave Server
 Copyright 2009 Patrick Schneider <patrick.p2k.schneider@gmail.com>

 PyGoWave XMPP component service.
 Copyright 2009 Markus Wagner  <murk@ferrum-et-magica.de>

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.

 To be included in the pygowave.tac's application using a ServiceManager

"""

import time
import datetime
from twisted.words.protocols.jabber import jid, xmlstream
from twisted.application import internet, service
from twisted.internet import interfaces, defer, reactor
from twisted.python import log
from twisted.words.xish import domish
from twisted.words.xish import xpath
from twisted.words.protocols.jabber.ijabber import IService
from twisted.words.protocols.jabber import component

from zope.interface import Interface, implements

from django.utils import simplejson

import common_pb2
import base64

# includes fro txamqp
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import ClientCreator
from txamqp.protocol import AMQClient
from txamqp.client import TwistedDelegate
import txamqp.spec

PRESENCE = '/presence' # this is an global xpath query to use in an observer
MESSAGE  = '/message'  # message xpath 
IQ       = '/iq'       # iq xpath

#FIXME - get this from settings file
jid = 'wave.ferrum-et-magica.de'


class LogService(component.Service):
    """
    A service to log incoming and outgoing xml to and from our XMPP component.

    """
    
    def transportConnected(self, xmlstream):
        xmlstream.rawDataInFn = self.rawDataIn
        xmlstream.rawDataOutFn = self.rawDataOut

    def rawDataIn(self, buf):
        log.msg("%s - RECV: %s" % (str(time.time()), unicode(buf, 'utf-8').encode('ascii', 'replace')))

    def rawDataOut(self, buf):
        log.msg("%s - SEND: %s" % (str(time.time()), unicode(buf, 'utf-8').encode('ascii', 'replace')))


class WaveFederationService(component.Service):
    """
    PyGoWave XMPP component service using twisted words.

    """
    implements(IService)


    def __init__(self):
        # XEP-0184 says we MUST include the feature if we use/support it
        self.features = { 'urn:xmpp:receipts': None
        }
        # No registration support for now
        # self.registrationManager = register.RegistrationManager(self)

        self.jabberId = 'wave.ferrum-et-magica.de'

        host = 'localhost'
        port = 5672
        vhost = '/'
        username = 'pygowave_xmpp'
        password = 'pygowave_xmpp'

        spec = txamqp.spec.load('amqp0-8.xml')

        delegate = TwistedDelegate()

        d = ClientCreator(reactor, AMQClient, delegate=delegate, vhost=vhost,
                spec=spec).connectTCP(host, port)

        d.addCallback(self.gotAMQPConnection, username, password)

        
    def componentConnected(self, xmlstream):
        """
        This method is called when the componentConnected event gets called.
        That event gets called when we have connected and authenticated with the XMPP server.
        """

        self.jabberId = xmlstream.authenticator.otherHost
        self.xmlstream = xmlstream # set the xmlstream so we can reuse it
        
        xmlstream.addObserver(PRESENCE, self.onPresence, 1)
        xmlstream.addObserver(IQ, self.onIq, 1)
        xmlstream.addObserver(MESSAGE, self.onMessage, 1)
        #TODO: maybe add support for XCP Component Presence

    def onMessage(self, msg):
        """
        Act on the message stanza that has just been received.


        Response to wavelet-update should look like this:

        <message id="1-1" from="wave.acmewave.com" to="wave.initech-corp.com">
            <received xmlns="urn:xmpp:receipts"/>
        </message>
        """


        for el in msg.elements():
            if el.name == 'request':
                for wavelet_update in xpath.XPathQuery('/message/event/items/item/wavelet-update').queryForNodes(msg):
                    waveletId = wavelet_update.attributes['wavelet-name']

                for applied_delta in xpath.XPathQuery('/message/event/items/item/wavelet-update/applied-delta').queryForNodes(msg):
                    content = str(applied_delta) #holy api failure
                    pbop = common_pb2.ProtocolWaveletOperation()
                    pbop.ParseFromString(base64.b64decode(content))

                    print "received wavelet-update contained this operation(s):"
                    for desc, val in pbop.ListFields():
                        print desc.name, val

                reply = domish.Element((None, 'message'))
                reply.attributes['id'] = msg.attributes['id']
                reply.attributes['to'] = msg.attributes['from']
                reply.attributes['from'] = self.jabberId
                reply.addElement(('urn:xmpp:receipts', 'received'))

                self.xmlstream.send(reply)

        
    def onIq(self, iq):
        """
        Act on the iq stanza that has just been received.

        """

        jidfrom = iq.getAttribute('from')
        id = iq.getAttribute('id')

        for query in iq.elements():
            xmlns = query.uri

            if xmlns == 'http://jabber.org/protocol/disco#info':
                self.sendDiscoInfoResponse(to=jidfrom, id=id)


            for (feature, handler) in self.features.items():
                if xmlns == feature:
                    handler(iq)
        

    def sendDiscoInfoResponse(self, to, id):
        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'result'
        iq.attributes['to']   = to
        iq.attributes['from'] = jid
        iq.attributes['id']   = id

        query = iq.addElement('query')
        query.attributes['xmlns'] = 'http://jabber.org/protocol/disco#info'

        identity = query.addElement('identity')
#        identity.attributes['category'] = 'jabber:iq:register'
        identity.attributes['name']     = 'PyGoWave'

        for key in self.features.keys():
            feature = query.addElement('feature')
            feature.attributes['var'] = key        

        self.xmlstream.send(iq)


    def onPresence(self, prs):
        """
        Act on the presence stanza that has just been received.

        """

        pass


    def processAMQPMessage(self, msg, chan):
        """
        <message type='normal'
            from='wave.ferrum-et-magica.de'
            id='H_0' to='wavetester@ferrum-et-magica.de'>
            <request xmlns='urn:xmpp:receipts'/>
            <event xmlns='http://jabber.org/protocol/pubsub#event'>
                <items>
                    <item>
                        <wavelet-update
                            xmlns='http://waveprotocol.org/protocol/0.2/waveserver'
                            wavelet-name='CH0H59rYDc!conv+root'>
                            <applied-delta><![CDATA[ChJtdXJrdGVzdEBsb2NhbGhvc3Q=]]></applied-delta>
                        </wavelet-update>
                    </item>
                </items>
            </event>
        </message>

        """

        print 'WaveFederationService received: ' + msg.content.body + ' from channel #' + str(chan.id)


        #FIXME How to get the routing key the right way?
        rkey = msg[4]
        participant_conn_key, wavelet_id, message_category = rkey.split(".")
        body = simplejson.loads(msg.content.body)


        if body['type'] == 'WAVELET_ADD_PARTICIPANT':
            participant = body['property']

            if participant.endswith('@localhost'):
                to = 'wave.ferrum-et-magica.de'
            else:
                to = participant.split('@')[1]

            pbop = common_pb2.ProtocolWaveletOperation()
            pbop.add_participant = participant
            data = base64.b64encode(pbop.SerializeToString())

            message = domish.Element((None, 'message'))
            message.attributes['type'] = 'normal'
            message.attributes['to'] = to
            message.attributes['from'] = jid
            message.addUniqueId()

            request = message.addElement(('urn:xmpp:receipts', 'request'))
            event   = message.addElement(('http://jabber.org/protocol/pubsub#event', 'event'))

            items   = event.addElement((None, 'items'))

            item    = items.addElement((None, 'item'))

            wavelet_update = item.addElement(('http://waveprotocol.org/protocol/0.2/waveserver', 'wavelet-update'))
            wavelet_update.attributes['wavelet-name'] = wavelet_id

            applied_delta = wavelet_update.addElement((None, 'applied-delta'))
            applied_delta.addRawXml('<![CDATA[%s]]>' % (data))

            self.xmlstream.send(message)

        elif body['type'] == 'OPERATION_MESSAGE_BUNDLE':
            #TODO: lookup participants of the wave and send the update to their federation remote if they are not local
            to = 'wave.ferrum-et-magica.de'

            operations = body['property']['operations']
        
            # NOTE: the wavelet-update message is only used if the wavelet is hosted locally
            #       Operations for remote hosted wavelets must use a submit request
            for op in operations:
                # format the operations as "base64-encoded serialized protocol buffer" as the spec says
                pbop = common_pb2.ProtocolWaveletOperation() 
                data = base64.b64encode(pbop.SerializeToString())

                message = domish.Element((None, 'message'))
                message.attributes['type'] = 'normal'
                message.attributes['to'] = to
                message.attributes['from'] = jid
                message.addUniqueId()

                request = message.addElement(('urn:xmpp:receipts', 'request'))
                event   = message.addElement(('http://jabber.org/protocol/pubsub#event', 'event'))

                items   = event.addElement((None, 'items'))
            
                item    = items.addElement((None, 'item'))

                wavelet_update = item.addElement(('http://waveprotocol.org/protocol/0.2/waveserver', 'wavelet-update'))
                wavelet_update.attributes['wavelet-name'] = wavelet_id

                applied_delta = wavelet_update.addElement((None, 'applied-delta'))
                applied_delta.addRawXml('<![CDATA[%s]]>' % (data))

                self.xmlstream.send(message)
        

#    def processFeedData(self, title, entry):
#
#        subscriptions = Subscription.objects.filter(feed__title=title)
#        payload = "%s: %s %s" % (title, entry.title, entry.link)
#
#        for sub in subscriptions:
#            update = domish.Element(('jabber:client', 'message'))
#            update['to'] = sub.subscriber.get_profile().jabberid
#            update['from'] = jid
#            update['type'] = 'chat'
#
#            body = domish.Element((None, 'body'))
#            body.addContent(payload)
#            update.addChild(body)
#
#            self.xmlstream.send(update)
#
#
#
#    def getXmlRpcResource(self):
#        x = xmlrpc.XMLRPC()
#        x.xmlrpc_sendToken = self.registrationManager.sendToken
#
#        return x


    @inlineCallbacks
    def gotAMQPConnection(self, conn, username, password):
        print "Connected to broker."
        yield conn.authenticate(username, password)

        print "Authenticated. Ready to receive messages"
        chan = yield conn.channel(1)
        yield chan.channel_open()

        yield chan.queue_declare(queue="federation", durable=True, exclusive=False, auto_delete=False)
#        yield chan.exchange_declare(exchange="wavelet.topic", type="direct", durable=True, auto_delete=False)

        yield chan.queue_bind(queue="federation", exchange="wavelet.topic", routing_key="#.#.clientop")

        yield chan.basic_consume(queue='federation', no_ack=True, consumer_tag="testtag")

        queue = yield conn.queue("testtag")

#        self.processAMQPMessage('test')
        while True:
            msg = yield queue.get()
            yield self.processAMQPMessage(msg, chan)
            if msg.content.body == "STOP":
                break

        yield chan.basic_cancel("testtag")
        yield chan.channel_close()
        chan0 = yield conn.channel(0)
        yield chan0.connection_close()



