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
from twisted.words.protocols.jabber.client import IQ

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

        for wavelet_update in xpath.XPathQuery('/message/event/items/item/wavelet-update').queryForNodes(msg):
                    wavelet_name = wavelet_update.attributes['wavelet-name']

        for applied_delta in xpath.XPathQuery('/message/event/items/item/wavelet-update/applied-delta').queryForNodes(msg):
            content = str(applied_delta) #holy api failure
            
        applied_wavelet_delta = common_pb2.ProtocolAppliedWaveletDelta()
        applied_wavelet_delta.ParseFromString(base64.b64decode(content))

        print applied_wavelet_delta
        
        deltaProtocolBuffer = common_pb2.ProtocolWaveletDelta()
        deltaProtocolBuffer.ParseFromString(applied_wavelet_delta.signed_original_delta.delta)

        #TODO wrap this up in a function, we will need it several times
        waveletDomain, waveId, waveletId = wavelet_name.replace('wave://','').split('/')

        if '$' in waveId:
            waveDomain, waveId = waveId.split('$')
        else:
            waveDomain = waveletDomain

        #since this is an update to a remote hosted wavelet, we assume that the waveletDomain 
        #is the same as the domain in the signature 
        if self.service.remoteHosts.has_key(waveletDomain):
            remote = self.service.remoteHosts[waveletDomain]
            #FIXME: we only do signature checking if we have the certificates for the remote host
            # we should retreive them here by a get signer request before we continue
            if remote.verifier.verify(deltaProtocolBuffer.SerializeToString(), applied_wavelet_delta.signed_original_delta.signature[0].signature_bytes):
                print "SIGNATURE VERIFICATION OK"
            else:
                print "SIGNATURE VERIFICATION FAILED!"

        print deltaProtocolBuffer
        
        print waveDomain, waveId, waveletDomain, waveletId
        try:
            wave = Wave.objects.get(id=waveId)
            print "Wave with ID %s already exists" % (waveId)
        except:
            wave = Wave(id=waveId, domain=waveDomain)
            wave.save()

        try:
            #FIXME: the author of the delta is in most cases not the creator of the wavelet
            creator = Participant.objects.get(id=deltaProtocolBuffer.author)
        except:
            creator = Participant(id=deltaProtocolBuffer.author)
            creator.last_contact = datetime.datetime.now()
            creator.save()

        _id = waveId + '!' + waveletId
        try:
            wavelet = Wavelet.objects.get(id=_id)
        except:
            wavelet = Wavelet(id=_id, domain=waveletDomain)
            wavelet.creator=creator
            wavelet.wave=wave
            #TODO: participants should be added by applying the delta using OT
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

        #request the history for this wavelet based on the wavelets version
        #and the version of the received delta

        print "Need to request history for wavelet %s: version %s to %s" % (wavelet.wavelet_name(), wavelet.version, deltaProtocolBuffer.hashed_version.version)
        self.sendHistoryRequest(wavelet, wavelet.version, '', deltaProtocolBuffer.hashed_version.version, '')

        
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
        usually called when a result to one of our discovery requests is received

        @param {Element} iq result received
        """

        #FIXME: a deferred and checking the id of the request would be better
        for item in xpath.XPathQuery('/iq/query/item').queryForNodes(iq):

            q = domish.Element((None, 'iq'))
            q.attributes['from'] = self.service.jabberId
            q.attributes['type'] = 'get'
            q.attributes['to'] = item.attributes['jid']
            q.addUniqueId()

            query = q.addElement((NS_DISCO_INFO, 'query'))

            self.service.xmlstream.send(q)


    def onDiscoInfoResponse(self, iq):
        """
        received during service discovery 
        """

        for feature in xpath.XPathQuery('/iq/query/feature').queryForNodes(iq):
            if feature.attributes['var'] == NS_WAVE_SERVER:
                jid = iq.attributes['from']
                domain = jid[jid.find('.')+1:]  #trim the hostname and first . from the jid to get the domain
                self.service.remoteHosts[domain].onJidDiscovered(jid)


    def sendSubmitRequest(self, wavelet, data):
        """
        sends a submit request to the remote federation host
        called when a not locally hosted wave is changed by local participant

        @param {Wavelet} wavelet
        @param {String} data

        """

        remote_domain = wavelet.wavelet_name().split('/')[0]

        iq = domish.Element((None, 'iq'))
        iq.attributes['type'] = 'set'
        iq.attributes['from'] = self.service.jabberId
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

        self.service.sendToRemoteHost(remote_domain, iq)


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
        
        remote_domain = wavelet.wavelet_name().split('/')[0]
        #FIXME: "block" until discovery has been made instead of manually adding "wave."
        remote_domain = 'wave.' + remote_domain

        iq = IQ(self.service.xmlstream, 'get')
        iq.attributes['from'] = self.service.jabberId
        iq.addUniqueId()

        pubsub = iq.addElement((NS_PUBSUB, 'pubsub'))

        items = pubsub.addElement((None, 'items'))
        items.attributes['node'] = 'wavelet'

        delta_history = items.addElement((NS_WAVE_SERVER, 'delta-history'))
        delta_history.attributes['start-version'] = str(start_version)
        delta_history.attributes['start-version-hash'] = start_version_hash
        delta_history.attributes['end-version'] = str(end_version)
        delta_history.attributes['end-version-hash'] = end_version_hash
        delta_history.attributes['wavelet-name'] = wavelet.wavelet_name()
        if response_length_limit:
            delta_history.attributes['response-length-limit'] = response_length_limit

        # you gotta love twisted for that, but it bypasses our per-remote resend queue and discovery stuff
        #self.service.sendToRemoteHost(remote_domain, iq)

        iq.addCallback(self.onHistoryResponse, wavelet)
        iq.send(remote_domain)


    def onHistoryResponse(self, wavelet, iq):
        """
        React on incoming wavelet history - print out some info on received data, no saving atm
        
        @param {Wavelet} wavelet the wavelet object, this is passed by the sendHistoryRequest function
        @param {Element} iq the reply from the remote server, this is passed by Twisted's IQ callback feature
        """

        print "Received wavelet history for wavelet", wavelet

        for applied_delta in xpath.XPathQuery('/iq/pubsub/items/item/applied-delta').queryForNodes(iq):

            appliedDeltaProtocolBuffer = common_pb2.ProtocolAppliedWaveletDelta()
            appliedDeltaProtocolBuffer.ParseFromString(base64.b64decode(str(applied_delta)))

            #print appliedDeltaProtocolBuffer

            #if self.service.remoteHosts.has_key(waveletDomain):
            #    remote = self.service.remoteHosts[waveletDomain]
            #    #FIXME: we only do signature checking if we have the certificates for the remote host
            #    # we should retreive them here by a get signer request before we continue
            #    if remote.verifier.verify(deltaProtocolBuffer.SerializeToString(), applied_wavelet_delta.signed_original_delta.signature[0].signature_bytes):
            #        print "SIGNATURE VERIFICATION OK"
            #    else:
            #        print "SIGNATURE VERIFICATION FAILED"

            deltaProtocolBuffer = common_pb2.ProtocolWaveletDelta()
            deltaProtocolBuffer.ParseFromString(appliedDeltaProtocolBuffer.signed_original_delta.delta)

            #print deltaProtocolBuffer

        for commit_notice in xpath.XPathQuery('/iq/pubsub/items/item/commit-notice').queryForNodes(iq):
            print "Ignored:", commit_notice.toXml()

        for history_truncated in xpath.XPathQuery('/iq/pubsub/items/item/history-truncated').queryForNodes(iq):
            print "Ignored:", history_truncated.toXml()

