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

First start by importing the TLS Server Credential class::

    >>> from smc.administration.certificates.tls import TLSServerCredential

If you want to create a TLS Server Credential in steps, the process is as follows::

    tls = TLSServerCredential.create(name)    # Create the certificate element
    tls.import_certificate(certificate) # Import the certificate
    tls.import_private_key(private_key) # Import the private key
    tls.import_intermediate_certificate(intermediate) # Import intermediate certificate (optional)

Otherwise, use helper methods that allow you to do this in a single step.
    
For example, creating the TLS credential from certificate files::

    >>> tls = TLSServerCredential.import_signed(
                  name='server.test.local',
                  certificate='/pathto/server.crt',
                  private_key='/pathto/server.key',
                  intermediate=None)  # <-- You can also include intermediate certificates
    >>> tls
    TLSServerCredential(name=server.test.local)

.. note:: Certificate, private key and intermediate certificates can also be specified in raw
    string format and must start with the BEGIN CERTIFICATE, etc common syntax.

You can also import certificates from a certificate chain file. When doing so, the certificates
are expected to be in the order: server certificate, intermediate/s, root certificate. You can
optionally also add the private key to the chain file or provide it separately::

    tls = TLSServerCredential.import_from_chain(
        name='fromchain', certificate_file='/path/cert.chain',
        private_key='/path/priv.key')
        
.. note:: If multiple intermediate certificates are added, only the first one is imported
    into the TLS Server Credential. In addition, the root certificate is ignored and should
    be imported using :meth:`TLSCertificateAuthority.create`.
    
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
    
If you use an external CA for signing your certficiates, you can also import
that as a TLS Certificate Authority. The link between the certificates and
root CA will be made automatically::

    TLSCertificateAuthority.create(
        name='myrootca',
        certificate='/path/to/cert/or/string')

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
    ImportPrivateKey, ImportExportIntermediate, load_cert_chain, pem_as_string
from smc.api.exceptions import CertificateImportError, ActionCommandFailed
from smc.base.util import datetime_from_ms, element_resolver
from smc.base.structs import NestedDict
    

class TLSProfile(Element):
    """
    .. versionadded:: 0.6.2
        Requires SMC >= 6.4
    
    Represents a TLS Profile.
    Contains common parameters for establishing TLS based connections.
    TLS Profiles are used in various configuration areas such as SSL
    VPN portal and Active Directory (when using TLS) connections.
    """
    typeof = 'tls_profile'

    @classmethod
    def create(cls, name, tls_version, use_only_subject_alt_name=False,
        accept_wildcard=False, check_revocation=True, tls_cryptography_suites=None,
        crl_delay=0, ocsp_delay=0, ignore_network_issues=False,
        tls_trusted_ca_ref=None, comment=None):
        """
        Create a TLS Profile. By default the SMC will have a default NIST
        TLS Profile but it is also possible to create a custom profile to
        provide special TLS handling.
        
        :param str name: name of TLS Profile
        :param str tls_verison: supported tls verison, valid options are
            TLSv1.1, TLSv1.2, TLSv1.3
        :param bool use_only_subject_alt_name: Use Only Subject Alt Name
            when the TLS identity is a DNS name
        :param bool accept_wildcard: Does server identity check accept wildcards
        :param bool check_revocation: Is certificate revocation checked
        :param str,TLSCryptographySuite tls_cryptography_suites: allowed cryptography
            suites for this profile. Uses NIST profile if not specified
        :param int crl_delay: Delay time (hours) for fetching CRL
        :param int ocsp_delay: Ignore OCSP failure for (hours)
        :param bool ignore_network_issues: Ignore revocation check failures
            due to network issues
        :param list tls_trusted_ca_ref: Trusted Certificate Authorities, empty
            list means trust any
        :param str comment: optional comment
        :raises CreateElementFailed: failed to create element with reason
        :raises ElementNotFound: specified element reference was not found
        :rtype: TLSProfile
        """
        json = {
            'name': name,
            'tls_version': tls_version,
            'use_only_subject_alt_name': use_only_subject_alt_name,
            'accept_wildcard': accept_wildcard,
            'check_revocation': check_revocation,
            'tls_cryptography_suites': element_resolver(tls_cryptography_suites) or \
                element_resolver(TLSCryptographySuite.objects.filter('NIST').first()),
            'crl_delay': crl_delay,
            'ocsp_delay': ocsp_delay,
            'ignore_network_issues': ignore_network_issues,
            'tls_trusted_ca_ref': element_resolver(tls_trusted_ca_ref) or [],
            'comment': comment}
    
        return ElementCreator(cls, json)


class TLSIdentity(NestedDict):
    """
    .. versionadded:: 0.6.2
        Requires SMC >= 6.4
    
    A TLS Identity represents a field and value pair that will
    be used to validate a TLS certificate. This can be used in
    various areas where TLS is used such as VPN.
    
    Valid tls field types are:
        
        DNSName
        IPAddress
        CommonName
        DistinguishedName
        SHA-1
        SHA-256
        SHA-512
        MD5
        Email
        user_principal_name
    
    """
    def __init__(self, tls_field, tls_value):
        data = {'tls_field': tls_field, 'tls_value': tls_value}
        super(TLSIdentity, self).__init__(data=data)
        

class TLSCryptographySuite(Element):
    """
    This represents a TLS Cryptography Suite Set used in various
    configurations that require a TLS Profile such as SSL VPN
    Tunneling, Reverse Web Proxy, ActiveDirectory TLS, etc.
    """
    typeof = 'tls_cryptography_suite_set'

    @staticmethod
    def ciphers(from_suite=None):
        """
        This is a helper method that will return all of the cipher
        strings used in a specified TLSCryptographySuite or returns
        the system default NIST profile list of ciphers. This can
        be used as a helper to identify the ciphers to specify/add
        when creating a new TLSCryptographySuite.
        
        :rtype: dict
        """
        suite = from_suite or TLSCryptographySuite.objects.filter(
            'NIST').first()
        return suite.data.get('tls_cryptography_suites')
    
    @classmethod
    def create(cls, name, comment=None, **ciphers):
        """
        Create a new TLSCryptographySuite. The ciphers kwargs should
        be a dict with the cipher suite string as key and boolean value
        to indicate if this cipher should be enabled.
        To obtain the valid cipher suite string name, use the following
        method::
        
            cipher_strings = TLSCryptographySuite.ciphers()
            
        Then to create a custom cipher suite, provide the ciphers as a
        dict of kwargs. In this example, create a TLS Crypto Suite that
        only enables AES 256 bit ciphers::
        
            only256 = dict(((cipher, True) for cipher in TLSCryptographySuite.ciphers()
                if 'aes_256' in cipher))
            
            mytls = TLSCryptographySuite.create(name='mytls', **only256)
        
        :param str name: name of this TLS Crypto suite
        :param dict ciphers: dict of ciphers with cipher string as key and
            bool as value, True enables the cipher
        :raises CreateElementFailed: failed to create element with reason
        :rtype: TLSCryptographySuite
        """
        json = {
            'name': name,
            'comment': comment,
            'tls_cryptography_suites': ciphers}
        
        return ElementCreator(cls, json) 
            

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
    
    @classmethod
    def create(cls, name, certificate):
        """
        Create a TLS CA. The certificate must be compatible with OpenSSL
        and be in PEM format. The certificate can be either a file with
        the Root CA, or a raw string starting with BEGIN CERTIFICATE, etc.
        When creating a TLS CA, you must also import the CA certificate. Once
        the CA is created, it is possible to import a different certificate to
        map to the CA if necessary.
        
        :param str name: name of root CA
        :param str,file certificate: The root CA contents
        :raises CreateElementFailed: failed to create the root CA
        :raises ValueError: if loading from file and no certificates present
        :raises IOError: cannot find specified file for certificate
        :rtype: TLSCertificateAuthority
        """
        json = {'name': name,
                'certificate': certificate if pem_as_string(certificate) else \
                    load_cert_chain(certificate)[0][1].decode('utf-8')}
        
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
    
    :ivar str certificate_state: State of the certificate. Available states are
        'request' and 'certificate'. If the state is 'request', this represents a
        CSR and needs to be signed.
    
    """
    typeof = 'tls_server_credentials'
    
    @classmethod
    def create(cls, name):
        """
        Create an empty certificate. This will only create the element
        in the SMC and will then require that you import the server
        certificate, intermediate (optional) and private key.
        
        .. seealso:: :meth:`~import_signed` and :meth:`~import_from_chain`.
        
        :raises CreateElementFailed: failed creating element
        :rtype: TLSServerCredential
        """
        json = {'name': name,
                'certificate_state': 'certificate'}
        
        return ElementCreator(cls, json)
        
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
        try:
            tls.self_sign()
        except ActionCommandFailed:
            tls.delete()
            raise
        return tls
    
    @classmethod
    def import_signed(cls, name, certificate, private_key, intermediate=None):
        """
        Import a signed certificate and private key to SMC, and optionally
        an intermediate certificate.
        The certificate and the associated private key must be compatible
        with OpenSSL and be in PEM format. The certificate and private key
        can be imported as a raw string, file path or file object.
        If importing as a string, be sure the string has carriage returns after
        each line and the final `END CERTIFICATE` line.
        
        Import a certificate and private key::
        
            >>> tls = TLSServerCredential.import_signed(
                    name='server2.test.local',
                    certificate='mydir/server.crt',
                    private_key='mydir/server.key')
            >>> tls
            TLSServerCredential(name=server2.test.local)   
        
        :param str name: name of TLSServerCredential
        :param str certificate: fully qualified to the certificate file, string or file object
        :param str private_key: fully qualified to the private key file, string or file object
        :param str intermediate: fully qualified to the intermediate file, string or file object
        :raises CertificateImportError: failure during import
        :raises CreateElementFailed: failed to create credential
        :raises IOError: failure to find certificate files specified
        :rtype: TLSServerCredential
        """
        tls = TLSServerCredential.create(name)
        try:
            tls.import_certificate(certificate)
            tls.import_private_key(private_key)
            if intermediate is not None:
                tls.import_intermediate_certificate(intermediate)
        except CertificateImportError:
            tls.delete()
            raise
        return tls
    
    @classmethod
    def import_from_chain(cls, name, certificate_file, private_key=None):
        """
        Import the server certificate, intermediate and optionally private
        key from a certificate chain file. The expected format of the chain
        file follows RFC 4346.
        In short, the server certificate should come first, followed by
        any intermediate certificates, optionally followed by
        the root trusted authority. The private key can be anywhere in this
        order. See https://tools.ietf.org/html/rfc4346#section-7.4.2.
        
        .. note:: There is no validation done on the certificates, therefore
            the order is assumed to be true. In addition, the root certificate
            will not be imported and should be separately imported as a trusted
            root CA using :class:`~TLSCertificateAuthority.create`
        
        If the certificate chain file has only two entries, it is assumed to
        be the server certificate and root certificate (no intermediates). In
        which case only the certificate is imported. If the chain file has
        3 or more entries (all certificates), it will import the first as the
        server certificate, 2nd as the intermediate and ignore the root cert.
        
        You can optionally provide a seperate location for a private key file
        if this is not within the chain file contents.
        
        .. warning:: A private key is required to create a valid TLS Server
            Credential.
        
        :param str name: name of TLS Server Credential
        :param str certificate_file: fully qualified path to chain file or file object
        :param str private_key: fully qualified path to chain file or file object
        :raises IOError: error occurred reading or finding specified file
        :raises ValueError: Format issues with chain file or empty
        :rtype: TLSServerCredential
        """
        contents = load_cert_chain(certificate_file)
        for pem in list(contents):
            if b'PRIVATE KEY' in pem[0]:
                private_key = pem[1]
                contents.remove(pem)
        
        if not private_key:
            raise ValueError('Private key was not found in chain file and '
                'was not provided. The private key is required to create a '
                'TLS Server Credential.')

        if contents:
            if len(contents) == 1:
                certificate = contents[0][1]
                intermediate = None
            else:
                certificate = contents[0][1]
                intermediate = contents[1][1]
        else:
            raise ValueError('No certificates found in certificate chain file. Did you '
                'provide only a private key?')
        
        tls = TLSServerCredential.create(name)
        try:
            tls.import_certificate(certificate)
            tls.import_private_key(private_key)
            if intermediate is not None:
                tls.import_intermediate_certificate(intermediate)
        except CertificateImportError:
            tls.delete()
            raise
        return tls
    
    def self_sign(self):
        """
        Self sign the certificate in 'request' state. 
        
        :raises ActionCommandFailed: failed to sign with reason
        """
        return self.make_request(
            method='create',
            resource='self_sign')

    @property
    def valid_from(self):
        """
        .. versionadded:: 0.6.0
            Requires SMC version >= 6.3.4
        
        The valid from datetime for this TLS Server Credential.
        
        :rtype: datetime.datetime
        """
        return datetime_from_ms(self.data.get('valid_from'))
    
    @property
    def valid_to(self):
        """
        .. versionadded:: 0.6.0
            Requires SMC version >= 6.3.4
        
        The expiration (valid to) datetime for this TLS Server Credential.
        
        :rtype: datetime.datetime
        """
        return datetime_from_ms(self.data.get('valid_to'))

    
class ClientProtectionCA(ImportPrivateKey, ImportExportCertificate, Element):
    """
    Client Protection Certificate Authority elements are used to inspect TLS
    traffic between an internal client and an external server for outbound
    decryption.

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
    
    @classmethod
    def import_signed(cls, name, certificate, private_key):
        """
        Import a signed certificate and private key as a client protection CA.
        
        This is a shortcut method to the 3 step process:
        
            * Create CA with name
            * Import certificate
            * Import private key
        
        Create the CA::
        
            ClientProtectionCA.import_signed(
                name='myclientca',
                certificate_file='/pathto/server.crt'
                private_key_file='/pathto/server.key')
            
        :param str name: name of client protection CA 
        :param str certificate_file: fully qualified path or string of certificate
        :param str private_key_file: fully qualified path or string of private key
        :raises CertificateImportError: failure during import
        :raises IOError: failure to find certificate files specified
        :rtype: ClientProtectionCA
        """
        ca = ClientProtectionCA.create(name=name)
        try:
            ca.import_certificate(certificate)
            ca.import_private_key(private_key)
        except CertificateImportError:
            ca.delete()
            raise
        return ca
    
    @classmethod
    def create(cls, name):
        """
        Create a client protection CA. Once the client protection CA is
        created, to activate you must then call import_certificate and
        import_private_key. Or optionally use the convenience classmethod
        :meth:`~import_signed`.
        
        :raises CreateElementFailed: failed to create base Client CA
        :rtype: ClientProtectionCA
        """
        json = {'name': name}
        
        return ElementCreator(cls, json)

    @classmethod
    def create_self_signed(cls, name, password, public_key_algorithm='rsa',
            life_time=365, key_length=2048, **kwargs):
        """
        .. versionchanged:: 0.7.0
        
            `prefix` argument deprecated in SMC > 6.5.1
        
        Create a self signed client protection CA. To prevent browser warnings during
        decryption, you must trust the signing certificate in the client browsers.
        
        :param str name: Name of this ex: "SG Root CA" Used as Key.
            Real common name will be derivated at creation time with a uniqueId.
        :param str password: password for private key
        :param public_key_algorithm: public key algorithm, either rsa, dsa or ecdsa
        :param str,int life_time: lifetime in days for CA
        :param int key_length: length in bits, either 1024 or 2048
        :raises CreateElementFailed: creating element failed
        :raises ActionCommandFailed: failed to self sign the certificate
        :rtype: ClientProtectionCA
        """
        json = {'key_name': name,
                'password': password,
                'life_time': life_time,
                'key_size': key_length,
                'algorithm': public_key_algorithm, **kwargs}
    
        tls = ClientProtectionCA.create(name)
        try:
            tls.make_request(
                method='create',
                json=json,
                resource='generate_self_signed_cert')
        except ActionCommandFailed:
            tls.delete()
            raise
        return tls

