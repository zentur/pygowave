from crypto import VerifierFromString

class RemoteHost(object):
    """
    Object representing a remote host, used to
    - implement a per-host resend queue
    - storing received certificates
    """

    def __init__(self, domain):
        self.domain = domain
        self.certificates = []

    def updateCertificates(self, certificates):
        """
        certificates comes as a list of strings
        """
        print "Updating certificates for host/domain:", self.domain
        self.certificates = certificates

        self.verifier = VerifierFromString(certificates)

