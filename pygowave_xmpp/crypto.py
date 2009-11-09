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

import hashlib
import base64
from M2Crypto.X509 import load_cert, load_cert_string, X509_Stack
from M2Crypto.RSA import load_key


class Signer(object):
    """
    TODO

    Certificates are stored as a list of M2Crypto's x509 objects
    """


    def __init__(self, certfile, keyfile):
        """
        """

        self.load_certificates(certfile)
        self.load_keyfile(keyfile)

        #TODO make algorithm configurable
        self.algorithm = hashlib.sha1
        pass


    def sign(self, payload):
        """
        Sign the payload with this signer's private key.

        @param {payload} the data to be signed
        """

        h = hashlib.sha1()
        h.update(payload)
        payload = h.digest()

        return self.private_key.sign(payload, algo='sha1')


    def get_signer_id(self):
        """
        Return the signer id of this signer
        """

        return self.signer_id


    def _calculate_signer_id(self):
        """
        The signer id is the base64 encoded hash of the pki-path of this signer:

        The pki path is defined as a ASN1 encoded sequence of certificates, where the
        first certificate is the "nearest" (e.g. the one generated for this very server)
        and the following are the rest of the certificate chain up to the CA's cert
        """
        #FIXME: still broken
        stack = X509_Stack()
        seq = '0\016'

        for cert in self.certificates:
            stack.push(cert)
            seq += '\026\005' + cert.as_der()
        h = hashlib.sha1()
        h.update(seq)
        signer_id = h.digest()

        self.signer_id = signer_id


    def get_cerfificate_chain(self):
        #return self.certificates
        return ['some_certificate']


    def load_certificates(self, certfile):
        """
        We load the certificate from the file provided in PEM format,
        we may need to load more than one file but one's complex enough for testing ;)

        after the certificates are loaded, we calculate the signer id
        """

        self.certificates = []

        certificate = load_cert(certfile)
    
        self.certificates.append(certificate)

        self._calculate_signer_id()


    def load_keyfile(self, keyfile):
        """
        """

        self.private_key = load_key('cert.key')


class Verifier(object):
    """
    used to verify signatures of incoming deltas
    like in the Signer, the certificates are a list of X509 objects
    """

    def __init__(self, certificates):
        """
        """
        self.certificates = certificates
        #we retreive the public key to decrypt the message from the first certificate in the list
        self.public_key = self.certificates[0].get_pubkey()
        self.algorithm = hashlib.sha1


    def verify(self, payload, signature):
        """
        verify a signature by comparing the digested payload with decrypted signature
        """

        self.public_key.reset_context(md='sha1')
        self.public_key.verify_init()
        self.public_key.verify_update(payload)

        return self.public_key.verify_final(signature)

def split_len(seq, length):
    return [seq[i:i+length] for i in range(0, len(seq), length)]

def VerifierFromString(certificates):
    """
    convert certificates from a list of strings to a list of X509 objects and return a
    Verifier with these certificates
    """

    l = []
    for cert in certificates:
        #FIXME: ugly to add those strings here
        
        x509 = load_cert_string('-----BEGIN CERTIFICATE-----\n'+'\n'.join(split_len(cert,64))+'\n-----END CERTIFICATE-----')
        l.append(x509)

    return Verifier(l)

