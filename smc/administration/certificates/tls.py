"""
TLS module provides interactions related to importing TLS Server Credentials
for inbound SSL decryption, as well as client protection certificates used
for outbound decryption.

To properly decrypt inbound TLS connections, you must provide the Stonesoft FW
with a valid certificate and private key. Within SMC these certificate types are
known as TLS Server Credentials.

Once you have imported these certificates, you must then assign them to the
relevant engines that will perform the decryption services. Lastly you will
need a rule that enables HTTPS with decryption.

Example of importing a pre-existing certificate and private key pair::

    >> from smc.administration.certificates.tls import TLSServerCredential
    >>> tls = TLSServerCredential.import_signed(
                  name='server.test.local',
                  certificate='/pathto/server.crt',
                  private_key='/pathto/server.key',
                  intermediate=None)  # <-- You can also include intermediate certificates
    >>> tls
    TLSServerCredential(name=server.test.local)

.. note:: Certificates can also be imported in string format and must start with the
    -----BEGIN CERTIFICATE----- common syntax.

It is also possible to create self signed certificates using the SMC CA::

    >>> tls = TLSServerCredential.create_self_signed(
        name='server.test.local', common_name='CN=server.test.local')
    >>> tls
    TLSServerCredential(name=server.test.local)

If you would rather use the SMC to generate the CSR and have the request signed by an
external CA you can call :meth:`TLSServerCredential.create_csr` and export the request::

    >>> tls = TLSServerCredential.create_csr(name='public.test.local', common_name='CN=public.test.local')
    >>> tls.certificate_export()
    '-----BEGIN CERTIFICATE REQUEST-----
    MIIEXTCCAkcCAQAwHDEaMBgGA1UEAwwRcHVibGljLnRlc3QubG9jYWwwggIiMA0G
    CSqGSIb3DQEBAQUAA4ICDwAwggIKAoICAQC68xcXrWQ5E25nkTfmgmPQiWVPwf
    ....
    ....
    -----END CERTIFICATE REQUEST-----'
    
Optionally export the request to a local file::

    >>> tls = TLSServerCredential.create_csr(
        name='public2.test.local', common_name='CN=public2.test.local')
    >>> tls.certificate_export(filename='public2.test.local.csr')

Once you have the TLS Server Credentials within SMC, you can then assign them to
the relevant engines::

    >>> from smc.core.engine import Engine
    >>> from smc.administration.certificates import TLSServerCredential
    >>> engine = Engine('myfirewall')
    >>> engine.tls_inspection.add_tls_credential([TLSServerCredential('public.test.local'), TLSServerCredential('server.test.local')])
    >>> engine.tls_inspection.server_credentials
    [TLSServerCredential(name=public.test.local), TLSServerCredential(name=server.test.local)]

.. note:: It is possible to import and export certificates from the SMC, but it is not
    possible to export private keys.
"""
from smc.base.model import Element, ElementCreator
from smc.administration.certificates.tls_common import ImportExportCertificate, \
    ImportPrivateKey, ImportExportIntermediate
    
    
class TLSCertificateAuthority(ImportExportCertificate, Element):
    """
    TLS Certificate authorities. When using TLS Server Credentials for
    decryption, import the root CA for the any TLS Server certificates
    the leverage the root CA.
    
    :ivar str certificate: base64 encoded certificate for this CA
    :ivar bool crl_checking_enabled: whether CRL checking is turned on
    :ivar bool internal_ca: is this an internal CA (default: false)
    :ivar bool oscp_checking_enabled: is OSCP validation enabled
    """
    typeof = 'tls_certificate_authority'
    
    def __init__(self, name, **meta):
        super(TLSCertificateAuthority, self).__init__(name, **meta)
    
    @classmethod
    def create(cls, name, certificate):
        """
        Create a TLS CA. The certificate can be either a file with
        the Root CA, or a string starting with -----BEGIN CERTIFICATE, etc.
        When creating a TLS CA, you must also import the CA certificate. Once
        the CA is created, it is possible to import a different certificate to
        map to the CA if necessary.
        
        :param str name: name of root CA
        :param str,file certificate: The root CA contents
        :raises CreateElementFailed: failed to create the root CA
        :rtype: TLSCertificateAuthority
        """
        json = {'name': name,
                'certificate': certificate}
        
        return ElementCreator(cls, json)
    

class TLSServerCredential(ImportExportIntermediate, ImportPrivateKey,
                          ImportExportCertificate, Element):
    """ 
    If you want to inspect TLS traffic for which an internal server is the
    destination, you must create a TLS Credentials element to store the
    private key and certificate of the server.

    The private key and certificate allow the firewall to decrypt TLS traffic
    for which the internal server is the destination so that it can be inspected.
    
    After a TLSServerCredential has been created, you must apply this to the
    engine performing decryption and create the requisite policy rule that uses
    SSL decryption.
    
    :ivar str certificate_state: State of the certificate. Available states are 'request' and
        'certificate'. If the state is 'request', this represents a CSR and needs to be signed.
    
    """
    typeof = 'tls_server_credentials'
    
    def __init__(self, name, **meta):
        super(TLSServerCredential, self).__init__(name, **meta)
    
    @classmethod
    def create_self_signed(cls, name, common_name, public_key_algorithm='rsa',
            signature_algorithm='rsa_sha_512', key_length=4096):
        """
        Create a self signed certificate. This is a convenience method that
        first calls :meth:`~create_csr`, then calls :meth:`~self_sign` on the
        returned TLSServerCredential object.
        
        :param str name: name of TLS Server Credential
        :param str rcommon_name: common name for certificate. An example
            would be: "CN=CommonName,O=Organization,OU=Unit,C=FR,ST=PACA,L=Nice".
            At minimum, a "CN" is required.
        :param str public_key_algorithm: public key type to use. Valid values
            rsa, dsa, ecdsa.
        :param str signature_algorithm: signature algorithm. Valid values
            dsa_sha_1, dsa_sha_224, dsa_sha_256, rsa_md5, rsa_sha_1, rsa_sha_256,
            rsa_sha_384, rsa_sha_512, ecdsa_sha_1, ecdsa_sha_256, ecdsa_sha_384,
            ecdsa_sha_512. (Default: rsa_sha_512)
        :param int key_length: length of key. Key length depends on the key
            type. For example, RSA keys can be 1024, 2048, 3072, 4096. See SMC
            documentation for more details.
        :raises CreateElementFailed: failed to create CSR
        :raises ActionCommandFailed: Failure to self sign the certificate
        :rtype: TLSServerCredential
        """
        tls = TLSServerCredential.create_csr(name=name, common_name=common_name,
            public_key_algorithm=public_key_algorithm, signature_algorithm=signature_algorithm,
            key_length=key_length)
        tls.self_sign()
        return tls
   
    @classmethod
    def create_csr(cls, name, common_name, public_key_algorithm='rsa',
               signature_algorithm='rsa_sha_512', key_length=4096):
        """
        Create a certificate signing request. 
        
        :param str name: name of TLS Server Credential
        :param str rcommon_name: common name for certificate. An example
            would be: "CN=CommonName,O=Organization,OU=Unit,C=FR,ST=PACA,L=Nice".
            At minimum, a "CN" is required.
        :param str public_key_algorithm: public key type to use. Valid values
            rsa, dsa, ecdsa.
        :param str signature_algorithm: signature algorithm. Valid values
            dsa_sha_1, dsa_sha_224, dsa_sha_256, rsa_md5, rsa_sha_1, rsa_sha_256,
            rsa_sha_384, rsa_sha_512, ecdsa_sha_1, ecdsa_sha_256, ecdsa_sha_384,
            ecdsa_sha_512. (Default: rsa_sha_512)
        :param int key_length: length of key. Key length depends on the key
            type. For example, RSA keys can be 1024, 2048, 3072, 4096. See SMC
            documentation for more details.
        :raises CreateElementFailed: failed to create CSR
        :rtype: TLSServerCredential
        """
        json = {
            'name': name,
            'info': common_name,
            'public_key_algorithm': public_key_algorithm,
            'signature_algorithm': signature_algorithm,
            'key_length': key_length,
            'certificate_state': 'initial'
        }
        return ElementCreator(cls, json)
    
    @classmethod
    def import_signed(cls, name, certificate, private_key, intermediate=None):
        """
        Import a signed certificate and private key file to SMC, and optiionally
        an intermediate certificate.
        The certificate and the associated private key must be compatible
        with OpenSSL and be in PEM format. If importing as a string, be 
        sure the string has carriage returns after each line and the final
        -----END CERTIFICATE----- line.
        
        Import a certificate and private key::
        
            >>> tls = TLSServerCredential.import_signed(
                    name='server2.test.local',
                    certificate_file='mydir/server.crt',
                    private_key_file='mydir/server.key')
            >>> tls
            TLSServerCredential(name=server2.test.local)   
        
        :param str name: name of TLSServerCredential
        :param str certificate: fully qualified to the certificate file or string
        :param str private_key: fully qualified to the private key file or string
        :raises CertificateImportError: failure during import
        :raises IOError: failure to find certificate files specified
        :rtype: TLSServerCredential
        """
        json = {'name': name,
                'certificate_state': 'certificate'}
        
        tls = ElementCreator(cls, json)
        tls.import_certificate(certificate)
        tls.import_private_key(private_key)
        if intermediate is not None:
            tls.import_intermediate_certificate(intermediate)
        return tls
    
    @classmethod
    def import_from_chain(cls, certificate_chain):
        """
        Import the server certificate and server key from a certificate
        chain file. The expected format of the chain file follows RFC 4346.
        In short, the server certificate should come first, followed by
        any ceritfying intermediate certificates, optionally followed by
        the root trusted authority. The private key can be anywhere in this
        order. See https://tools.ietf.org/html/rfc4346#section-7.4.2.
        """
        pass
    
    def self_sign(self):
        """
        Self sign the certificate in 'request' state. 
        
        :raises ActionCommandFailed: failed to sign with reason
        """
        return self.send_cmd(
            resource='self_sign')


class ClientProtectionCA(ImportPrivateKey, ImportExportCertificate, Element):
    """
    Client Protection Certificate Authority elements are used to inspect TLS
    traffic between an internal client and an external server.

    When an internal client makes a connection to an external server that uses
    TLS, the engine generates a substitute certificate that allows it to establish
    a secure connection with the internal client. The Client Protection Certificate
    Authority element contains the credentials the engine uses to sign the substitute
    certificate it generates.
    
    :ivar str certificate: base64 encoded certificate for this CA
    :ivar bool crl_checking_enabled: whether CRL checking is turned on
    :ivar bool internal_ca: is this an internal CA (default: false)
    :ivar bool oscp_checking_enabled: is OSCP validation enabled
    
    .. note :: If the engine does not use a signing certificate that is already
        trusted by users web browsers when it signs the substitute certificates it
        generates, users receive warnings about invalid certificates. To avoid these
        warnings, you must either import a signing certificate that is already trusted,
        or configure users web browsers to trust the engine signing certificate.
    """
    typeof = 'tls_signing_certificate_authority'
    
    def __init__(self, name, **meta):
        super(ClientProtectionCA, self).__init__(name, **meta)
    
    @classmethod
    def import_signed(cls, name, certificate_file, private_key_file):
        """
        Import a signed certificate and private key as a client protection CA.
        
        This is a shortcut method to the 3 step process:
        
            * Create protection CA
            * Import certificate
            * Import private key
        
        Create the CA::
        
            ClientProtectionCA.import_signed(
                name='myclientca',
                certificate_file='/pathto/server.crt'
                private_key_file='/pathto/server.key')
            
        :param str name: name of client protection CA 
        :param str certificate_file: fully qualified to the certificate file
        :param str private_key_file: fully qualified to the private key file
        :raises CertificateImportError: failure during import
        :raises IOError: failure to find certificate files specified
        :rtype ClientProtectionCA
        """
        ca = ClientProtectionCA.create(name=name)
        ca.certificate_import(certificate_file)
        ca.private_key_import(private_key_file)
        return ca
    
    @classmethod
    def create(cls, name):
        """
        Create a client protection CA. Once the client protection CA is
        created, to activate you must then call import_certificate and
        import_private_key. Or optionally use the convenience classmethod
        :meth:`~import_signed`.
        """
        json = {'name': name}
        
        return ElementCreator(cls, json)

    