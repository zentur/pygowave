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


def getHistoryHash(version, wavelet_name):
    """
    if the version of delta is 0, the history hash is simply the wavelet-name

    else take the hash from version-1, join the bytes of the applied delta, digest it, truncate it to 20bytes

    """
    hashKey = '%s%s' % (wavelet_name, version)
    if historyHashCache.has_key(hashKey):
        return historyHashCache[hashKey]


    print "getHistoryHash: version:", version

    #FIXME: a dummy author
    author = 'murk@localhost'

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


        #  = getHistoryHash(version - 1, wavelet_name)

        prev = version #- 1

        wavelet = Wavelet.objects.get(pk=waveId+'!'+waveletId)
        delta = Delta.objects.filter(wavelet=wavelet).get(version=prev)
        print delta

        d = getWaveletDelta(delta, wavelet_name, author)
        print "delta for version:", prev, d
        app_delta = getAppliedWaveletDelta(d)
        print "appliedDelta", app_delta
        prevHash = d.hashed_version.history_hash

        hashSizeBits = 160 #google does it, so do we

        history_hash = hashlib.sha256()
        history_hash.update(prevHash + app_delta.SerializeToString())

        h = history_hash.digest()[0:hashSizeBits/8]

        print "calculated hash for wavelet %s, version %s:" % (wavelet_name, prev)
        historyHashCache[hashKey] = h
        print repr(h)
        return h
        

def getWaveletDelta(_delta, wavelet_name, author):
    """
    Return an instance of ProtocolWaveletDelta

    @param {int} version the version this delta is meant to be applied to
    @param {String} operations in pygowave specific serialized JSON format
    @param {String} history_hash for the version this delta is applied to
    @param {String} author wave address of the author of that delta

    """
    version = _delta.version - 1
    operations = simplejson.loads(_delta.operations)

    return getWaveletDelta2(version, operations, wavelet_name, author)

def getWaveletDelta2(version, operations, wavelet_name, author):
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
    delta.hashed_version.history_hash = getHistoryHash(version, wavelet_name)
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

def getAppliedWaveletDelta(delta):

    app_delta = common_pb2.ProtocolAppliedWaveletDelta()
    app_delta.signed_original_delta.delta = delta.SerializeToString()

    sig = app_delta.signed_original_delta.signature.add()
    sig.signature_bytes = 'some signature bytes'
    sig.signer_id = 'some signer id'
    sig.signature_algorithm = common_pb2.ProtocolSignature.SHA1_RSA

    #HashedVersion is optional, so leave it for now
    app_delta.operations_applied = len(delta.operation)
    app_delta.application_timestamp = 123456789

    return app_delta

