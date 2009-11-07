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
        testid = '\xa0b\x920\xe1\x88\x1d\xd7\xc9JQ\xc9\x9es\xfd\xc0@\xce\x93\x8e'
        self.assertEqual(testid, self.signer.get_signer_id())


    def test_sign(self):
        """
        """
        teststring = 'n\xca\x04)Jl\xc5~\x96C)\xda\r\xf5\xb62\xc3\xe9\xfb\xe8V\xee\xa1\x9b\x1f\xb9\x93QM\'\xa0b\xbc\x05:9X\x97|\xd5\xd3\x9c\x94\xf4\xc5\x8df\xdc"F\xc7\x15N\x88\xfc\x1d\xf7/n%\xf8c\x9a&Cf\x8e\x0e\x0b\xbf>{-\xe6ZG.x4\x9fuz\x9d\xb2d\xd0\xeb\x9d~\r\xdf\xab\x0e,6\xf4\xd8mY\x1f$\xbd\xdc\x81\xd4\x81\x9dqE\xd3\x07\x12]\x81G\xfe\xdb\x83\xda\xbe[\xb4\x82\xec\xee\xce1\x8c'

        self.assertEqual(teststring, self.signer.sign('teststring'))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(SignerTestCase('test_load_certificates'))
    suite.addTest(SignerTestCase('test_get_signer_id'))
    suite.addTest(SignerTestCase('test_sign'))
    return suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())

