"""

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
import hashlib

from django.utils import simplejson

import common_pb2

#FIXME: We import Delta here to get the hashes fast, but hashing would be
#FIXME: perfect to put into the Delta model itself

from pygowave_server.models import Delta, Wavelet

#FIXME:
#FIXME: This code is ugly and misleading, this will be fixed once it is working
#FIXME:

historyHashCache = {}


def addDocumentInsertOperation(op, document_id, item_count, characters):
    """
    create a new operation with two components
    comp one skips the characters, comp two inserts a string
    at least, thats how i understand it ;)

    """

    op.mutate_document.document_id = document_id

    if item_count > 0:
        comp = op.mutate_document.document_operation.component.add()
        comp.retain_item_count = item_count

    comp = op.mutate_document.document_operation.component.add()
    comp.characters = characters


def getHistoryHash(version, wavelet_name, signer):
    """
    if the version of delta is 0, the history hash is simply the wavelet-name

    else take the hash from version-1, join the bytes of the applied delta, digest it, truncate it to 20bytes

    """
    hashKey = '%s%s' % (wavelet_name, version)
    if historyHashCache.has_key(hashKey):
        return historyHashCache[hashKey]


    print "getHistoryHash: version:", version

    #FIXME: a dummy author is used here, we need the author of each delta stored in the ORM
    author = 'murk@localhost'

    #FIXME: the numbering of versions is misleading, as the version stored in the delta is
    #the one the wavelet has AFTER applying, but history hashes work by using the version nummer
    #the delta is applied TO!

    #Specifies the length the calculated hash is truncated to (in bits)
    #Spec doesn't tell about it, but fedone does it, so do we
    hashSizeBits = 160 

    if version == 0:
        if wavelet_name.startswith('wave://'):
            return str(wavelet_name)
        else:
            return 'wave://' + str(wavelet_name)
    else:

        waveletDomain, waveId, waveletId = wavelet_name.replace('wave://','').split('/')

        if '$' in waveId:
            waveDomain, waveId = waveId.split('$')
        else:
            waveDomain = waveletDomain

        wavelet = Wavelet.objects.get(pk=waveId+'!'+waveletId)
        delta = Delta.objects.filter(wavelet=wavelet).get(version=version)

        d = getWaveletDelta(delta, author, signer)
        print "delta for version:", version, d
        app_delta = getAppliedWaveletDelta(d, signer)
        print "appliedDelta", app_delta
        prevHash = d.hashed_version.history_hash

        history_hash = hashlib.sha256()
        history_hash.update(prevHash + app_delta.SerializeToString())

        h = history_hash.digest()[0:hashSizeBits/8]

        print "calculated hash for wavelet %s, version %s:" % (wavelet_name, version)
        historyHashCache[hashKey] = h
        print repr(h)
        return h
        

def getWaveletDelta(delta, author, signer):
    """
    creates the delta from the models.Delta class

    @param {delta} Delta delta the ProtocolBuffer is created from
    @param {author} a dummy author used to fill the author field in the protocol buffer

    """

    version = delta.version - 1
    operations = simplejson.loads(delta.operations)
    wavelet_name = delta.wavelet.wavelet_name()

    return getWaveletDelta2(version, operations, wavelet_name, author, signer)


def getWaveletDelta2(version, operations, wavelet_name, author, signer):
    """
    Return an instance of ProtocolWaveletDelta

    @param {int} version the version this delta is meant to be applied to
    @param {String} operations in pygowave specific serialized JSON format
    @param {String} history_hash for the version this delta is applied to
    @param {String} author wave address of the author of that delta

    """

    #TODO: support for address_path
    print "getWaveletDelta:", version

    delta = common_pb2.ProtocolWaveletDelta()
    delta.hashed_version.version = version
    delta.hashed_version.history_hash = getHistoryHash(version, wavelet_name, signer)
    delta.author = author

    for item in operations:
        if item['type'] == 'DOCUMENT_INSERT':
            op = delta.operation.add()
            addDocumentInsertOperation(op, item['blipId'], item['index'], item['property'])
        else:
            print "FIXME: Replacing conversion of operation type %s to protocol buffer 'no_op'" % (item['type'])
            op = delta.operation.add()
            op.no_op = True

    return delta

def getAppliedWaveletDelta(delta, signer):

    app_delta = common_pb2.ProtocolAppliedWaveletDelta()
    app_delta.signed_original_delta.delta = delta.SerializeToString()

    sig = app_delta.signed_original_delta.signature.add()

    sig.signature_bytes = signer.sign(delta.SerializeToString())
    sig.signer_id = signer.get_signer_id()
    sig.signature_algorithm = common_pb2.ProtocolSignature.SHA1_RSA

    #HashedVersion is optional, so leave it for now
    app_delta.operations_applied = len(delta.operation)
    app_delta.application_timestamp = 123456789

    return app_delta

