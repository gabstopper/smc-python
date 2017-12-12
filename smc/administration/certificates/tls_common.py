"""
TLS Common module provides mixin methods that are common to certificate
handling in SMC.
Importing certificates and private keys can be done by providing a file
where the certificates/keys are stored, or providing in string format.
"""

import re
from smc.compat import unicode
from smc.base.util import save_to_file
from smc.api.exceptions import CertificateImportError, CertificateExportError
    

CERT_TYPES = (b'PRIVATE KEY', b'RSA PRIVATE KEY', b'CERTIFICATE')
    
_PEM_RE = re.compile(b"-----BEGIN (" + b"|".join(CERT_TYPES) + \
    b""")-----\r?.+?\r?-----END \\1-----\r?\n?""", re.DOTALL)
    
    
def pem_as_string(cert):
    cert = cert.encode('ascii') if isinstance(cert, unicode) else cert
    if re.match(_PEM_RE, cert):
        return True
    return False


class ImportExportCertificate(object):
    """
    Mixin to provide certificate import and export methods to relevant
    classes.
    """
    def import_certificate(self, certificate):
        """
        Import a valid certificate. Certificate can be either a file path
        or a string of the certificate. If string certificate, it must include
        the -----BEGIN CERTIFICATE----- string.
        
        :param str certificate_file: fully qualified path to certificate file
        :raises CertificateImportError: failure to import cert with reason
        :raises IOError: file not found, permissions, etc.
        :return: None
        """
        multi_part = 'signed_certificate' if self.typeof == 'tls_server_credentials'\
            else 'certificate'
        self.send_cmd(
            CertificateImportError,
            resource='certificate_import',
            headers = {'content-type': 'multipart/form-data'}, 
            files={ 
                    multi_part: open(certificate, 'rb') if not \
                        pem_as_string(certificate) else certificate
                })
    
    def export_certificate(self, filename=None):
        """
        Export the certificate. Returned certificate will be in string
        format. If filename is provided, the certificate will also be saved
        to the file specified.
        
        :rtype: str or None
        """
        result = self.read_cmd(
            CertificateExportError,
            raw_result=True,
            resource='certificate_export')
            
        if filename is not None:
            save_to_file(filename, result.content)
            return
    
        return result.content
    

class ImportExportIntermediate(object):
    """
    Mixin to provide import and export capabilities for intermediate
    certificates
    """
    def import_intermediate_certificate(self, certificate):
        self.send_cmd(
            CertificateImportError,
            resource='intermediate_certificate_import',
            headers = {'content-type': 'multipart/form-data'}, 
            files={ 
                'signed_certificate': open(certificate, 'rb') if not \
                    pem_as_string(certificate) else certificate
            })
    
    def export_intermediate_certificate(self, filename=None):
        """
        Export the intermediate certificate. Returned certificate will be in
        string format. If filename is provided, the certificate will also be
        saved to the file specified.
        
        :rtype: str or None
        """
        result = self.read_cmd(
            CertificateExportError,
            raw_result=True,
            resource='intermediate_certificate_export')
            
        if filename is not None:
            save_to_file(filename, result.content)
            return
    
        return result.content
    
    
class ImportPrivateKey(object):
    """
    Mixin to provide import capabilities to relevant classes that
    require private keys.
    """
    def import_private_key(self, private_key):
        """
        Import a private key. The private key can be a path to a file
        or the key in string format. If in string format, the key must
        start with -----BEGIN. Key types supported are PRIVATE RSA KEY
        and PRIVATE KEY.
        
        :param str private_key: fully qualified path to private key file
        :raises CertificateImportError: failure to import cert with reason
        :raises IOError: file not found, permissions, etc.
        :return: None
        """
        self.send_cmd(
            CertificateImportError,
            resource='private_key_import',
            headers = {'content-type': 'multipart/form-data'}, 
            files={ 
                'private_key': open(private_key, 'rb') if not \
                    pem_as_string(private_key) else private_key
            })
