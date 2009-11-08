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

"""
import base64
import datetime

from twisted.words.xish import domish, xpath

from django.utils import simplejson

import common_pb2
from pygowave_server.models import Wave, Wavelet, Participant, Delta
from wavefederationservice import NS_XMPP_RECEIPTS, NS_DISCO_INFO, NS_DISCO_ITEMS, NS_PUBSUB, NS_PUBSUB_EVENT, NS_WAVE_SERVER
from remotehost import RemoteHost

class WaveFederationRemote(object):
    """
    PyGoWave XMPP component service using twisted words.

    This is the federation remote part which according to the spec does the following:

    * It receives new wavelet operations pushed to it from the wave providers that host the wavelets.
    * It requests old wavelet operations from the hosting wave providers.
    * It submits wavelet operations to the hosting wave providers.

    """

    def __init__(self, service):
        self.service = service


    def onUpdateMessage(self, msg):
        """
        Act on the message stanza that has just been received.

        @param {Element} msg the message stanza received

        """

        if msg.attributes['type'] == 'error':
            #TODO Better error handling
            print "Error received"
            return

        for wavelet_update in xpath.XPathQuery('/message/event/items/item/wavelet-update').queryForNodes(msg):
                    wavelet_name = wavelet_update.attributes['wavelet-name']

        for applied_delta in xpath.XPathQuery('/message/event/items/item/wavelet-update/applied-delta').queryForNodes(msg):
            content = str(applied_delta) #holy api failure
            
        applied_wavelet_delta = common_pb2.ProtocolAppliedWaveletDelta()
        applied_wavelet_delta.ParseFromString(base64.b64decode(content))

        print applied_wavelet_delta
        
        deltaProtocolBuffer = common_pb2.ProtocolWaveletDelta()
        deltaProtocolBuffer.ParseFromString(applied_wavelet_delta.signed_original_delta.delta)

        remote_domain = 'fedone.ferrum-et-magica.de'
        if self.service.remoteHosts.has_key(remote_domain):
            remote = self.service.remoteHosts[remote_domain]
            #FIXME: we only do signature checking if we have the certificates for the remote host
            # we should retreive them here by a get signer request before we continue
            if remote.verifier.verify(deltaProtocolBuffer.SerializeToString(), applied_wavelet_delta.signed_original_delta.signature[0].signature_bytes):
                print "SIGNATURE VERIFICATION OK"
            else:
                print "SIGNATURE VERIFICATION FAILED!"

        print deltaProtocolBuffer
        
        #TODO wrap this up in a function, we will need it several times
        waveletDomain, waveId, waveletId = wavelet_name.replace('wave://','').split('/')

        if '$' in waveId:
            waveDomain, waveId = waveId.split('$')
        else:
            waveDomain = waveletDomain

        print waveDomain, waveId, waveletDomain, waveletId
        try:
            wave = Wave.objects.get(id=waveId)
            print "Wave with ID %s already exists" % (waveId)
        except:
            wave = Wave(id=waveId, domain=waveDomain)
            wave.save()

        try:
            #FIXME: get a real user here
            creator = Participant.objects.get(id='murk@fedone.ferrum-et-magica.de')
        except:
            creator = Participant(id='murk@fedone.ferrum-et-magica.de')
            creator.last_contact = datetime.datetime.now()
            creator.save()

        _id = waveId + '!' + waveletId
        try:
            wavelet = Wavelet.objects.get(id=_id)
        except:
            wavelet = Wavelet(id=_id, domain=waveletDomain)
            wavelet.creator=creator
            wavelet.wave=wave
            wavelet.participants.add(creator)
            wavelet.version=0
            wavelet.is_root = True
            wavelet.save()

        reply = domish.Element((None, 'message'))
        reply.attributes['id'] = msg.attributes['id']
        reply.attributes['to'] = msg.attributes['from']
        reply.attributes['from'] = self.service.jabberId
        reply.addElement(('urn:xmpp:receipts', 'received'))

        self.service.xmlstream.send(reply)

        
    def sendDiscoInfoResponse(self, iq):
        """

        """

        reply = domish.Element((None, 'iq'))
        reply.attributes['type'] = 'result'
        reply.attributes['from'] = self.service.jabberId
        reply.attributes['to']   = iq.attributes['from']
        reply.attributes['id']   = iq.attributes['id']

        query = reply.addElement((NS_DISCO_INFO, 'query'))

        identity = query.addElement('identity')
        identity.attributes['name']     = 'PyGoWave'
        identity.attributes['category'] = 'collaboration'
        identity.attributes['type']     = 'pygowave'

        for key in self.service.features.keys():
            feature = query.addElement('feature')
            feature.attributes['var'] = key        

        self.service.xmlstream.send(reply)


    def onDiscoInfoResponse(self, iq):
        """

        """

        pass


    def sendDiscoItemsResponse(self, iq):
        """

        """

        reply = domish.Element((None, 'iq'))
        reply.attributes['type'] = 'result'
        reply.attributes['from'] = self.service.jabberId
        reply.attributes['to']   = iq.attributes['from']
        reply.attributes['id']   = iq.attributes['id']

        query = reply.addElement((NS_DISCO_ITEMS, 'query'))

        #NOTE: i am not sure if this is allowed, but it "fixes" my
        #service discovery problem for the moment

        item = query.addElement((None, 'item'))
        item.attributes['jid'] = self.service.jabberId
        item.attributes['name'] = 'PyGoWave'

        self.service.xmlstream.send(reply)


    def onDiscoItemsResponse(self, iq):
        """

        """

        pass


    def sendSubmitRequest(self, wavelet, data):
        """
        sends a submit request to the remote federation host
        called when a not locally hosted wave is changed by local participant

        @param {Wavelet} wavelet
        @param {String} data

        """

        hoster = wavelet.wavelet_name().split('/')[0]

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'set'
        iq.attributes['from'] = self.service.jabberId
        iq.attributes['to']   = hoster
        iq.addUniqueId()

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))

        publish = pubsub.addElement((None, 'publish'))
        publish.attributes['node'] = 'wavelet'

        item = publish.addElement((None, 'item'))

        submit_request = item.addElement((NS_WAVE_SERVER, 'submit-request'))

        delta = submit_request.addElement((None, 'delta'))
        delta.attributes['wavelet-name'] = wavelet.wavelet_name()
        delta.addRawXml('<![CDATA[%s]]>' % (data))

        print "Submit request for wavelet %s: %s" % (wavelet, iq.toXml())

        self.service.xmlstream.send(iq)


    def sendHistoryRequest(self, wavelet, start_version, start_version_hash, 
                           end_version, end_version_hash, response_length_limit=None):
        """
        Request the history of a wavelet from the wavelet's hosting server

        @param {Wavelet} wavelet Wavelet the history is requested for
        @param {int} start_version Version the history should start at (including)
        @param {String} start_version_hash The version hash for the start version
        @param {int} end_version Version the history request should end at (excluding)
        @param {int} end_version_hash The version hash for the end version
        @param {int} response_length_limit Number of characters the history response's xml should have at max

        """
        
        hoster = wavelet.wavelet_name().split('/')[0]

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'get'
        iq.attributes['from'] = self.service.jabberId
        iq.attributes['to']   = hoster
        iq.addUniqueId()

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))

        items = publish.addElement((None, 'items'))
        items.attributes['node'] = 'wavelet'

        delta_history = items.addElement((NS_WAVE_SERVER, 'delta-history'))
        delta_history.attributes['start-version'] = start_version
        delta_history.attributes['start-version-hash'] = start_version_hash
        delta_history.attributes['end-version'] = end_version
        delta_history.attributes['end-version-hash'] = end_version_hash
        delta_history.attributes['wavelet-name'] = wavelet.wavelet_name()
        if response_length_limit:
            delta_history.attributes['response-length-limit'] = response_length_limit

        print "History request for wavelet %s: %s" % (wavelet, iq.toXml())

        self.service.xmlstream.send(iq)

