"""
unit testing code for pygowave's federation module
"""

import unittest

import crypto

class SignerTestCase(unittest.TestCase):

    def setUp(self):
        self.signer = crypto.Signer('cert.pem', 'cert.key')

    def test_load_certificates(self):
        """
        check that signer.certificates contains at least one element
        """

        self.assert_(len(self.signer.certificates) > 0)


    def test_get_signer_id(self):
        """
        """

        self.assertEqual('some_signer_id', self.signer.get_signer_id())


    def test_sign(self):
        """
        """

        self.assertEqual('\x86a\x82\xcfX\xec\xb2\xc2\xfa\xb1\x1c=\x99bb\xb6=\xf5\xd5\xfc', self.signer.sign('teststring'))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(SignerTestCase('test_load_certificates'))
    suite.addTest(SignerTestCase('test_get_signer_id'))
    suite.addTest(SignerTestCase('test_sign'))
    return suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())

