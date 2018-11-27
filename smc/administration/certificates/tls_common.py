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
    """
    Only return False if the certificate is a file path. Otherwise it
    is a file object or raw string and will need to be fed to the
    file open context.
    """
    if hasattr(cert, 'read'): # File object - return as is
        return cert
    cert = cert.encode('utf-8') if isinstance(cert, unicode) else cert
    if re.match(_PEM_RE, cert):
        return True
    return False


def load_cert_chain(chain_file):
    """ 
    Load the certificates from the chain file.
    
    :raises IOError: Failure to read specified file
    :raises ValueError: Format issues with chain file or missing entries
    :return: list of cert type matches
    """
    if hasattr(chain_file, 'read'):
        cert_chain = chain_file.read() 
    else:
        with open(chain_file, 'rb') as f:
            cert_chain = f.read()       
    
    if not cert_chain:
        raise ValueError('Certificate chain file is empty!')

    cert_type_matches = []
    for match in _PEM_RE.finditer(cert_chain):
        cert_type_matches.append((match.group(1), match.group(0)))
    
    if not cert_type_matches:
        raise ValueError('No certificate types were found. Valid types '
            'are: {}'.format(CERT_TYPES))

    return cert_type_matches
    

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
        self.make_request(
            CertificateImportError,
            method='create',
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
        
        :raises CertificateExportError: error exporting certificate
        :rtype: str or None
        """
        result = self.make_request(
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
        """
        Import a valid certificate. Certificate can be either a file path
        or a string of the certificate. If string certificate, it must include
        the -----BEGIN CERTIFICATE----- string.
        
        :param str certificate: fully qualified path or string 
        :raises CertificateImportError: failure to import cert with reason
        :raises IOError: file not found, permissions, etc.
        :return: None
        """
        self.make_request(
            CertificateImportError,
            method='create',
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
        
        :raises CertificateExportError: error exporting certificate, can occur
            if no intermediate certificate is available.
        :rtype: str or None
        """
        result = self.make_request(
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
        self.make_request(
            CertificateImportError,
            method='create',
            resource='private_key_import',
            headers = {'content-type': 'multipart/form-data'}, 
            files={ 
                'private_key': open(private_key, 'rb') if not \
                    pem_as_string(private_key) else private_key
            })
