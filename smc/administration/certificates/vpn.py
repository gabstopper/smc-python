"""
VPN Certificates are used by NGFW to identify the engines for VPN clients
and other VPN related connections. Each gateway certificate is signed by
a VPN CA and uses the default internal CA by default.
"""

from smc.base.model import Element, ElementCreator, SubElement, ElementRef
from smc.administration.certificates.tls_common import ImportExportCertificate
from smc.api.exceptions import CertificateError
from smc.base.util import element_resolver


class VPNCertificateCA(ImportExportCertificate, Element):
    """
    A VPN CA certificate is used to within VPN Profiles to validate
    site-to-site or client VPN connections. By default SMC will use
    an internal CA. Use this method to create your own CA as a trusted
    endpoint CA.
    
    :ivar str certificate: base64 encoded certificate for this CA
    :ivar bool crl_checking_enabled: whether CRL checking is turned on
    :ivar bool internal_ca: is this an internal CA (default: false)
    :ivar bool oscp_checking_enabled: is OSCP validation enabled
    """
    typeof = 'vpn_certificate_authority'
    
    @classmethod    
    def create(cls, name, certificate):
        """
        Create a new external VPN CA for signing internal gateway
        certificates.
        
        :param str name: Name of VPN CA
        :param str certificate: file name, path or certificate string.
        :raises CreateElementFailed: Failed creating cert with reason
        :rtype: VPNCertificateCA
        """
        json = {'name': name,
                'certificate': certificate}
        
        return ElementCreator(cls, json)
    

class GatewayCertificate(SubElement):
    """
    A Gateway Certificate repesents a certificate assigned to a
    NGFW certificate used for VPN endpoints. Gateway certificates
    are typically renewed automatically when the auto renew option
    is set on the engine. However you can also optionally force
    renew a gateway certificate, export, check the expiration, or
    find the certificate authority that signed this gateway certificate.
    
    :ivar certificate_authority: CA for this GatewayCertificate
    """
    typeof = 'gateway_certificate'
    certificate_authority = ElementRef('certificate_authority')
    
    @staticmethod
    def _create(self, common_name, public_key_algorithm='rsa',
            signature_algorithm='rsa_sha_512', key_length=2048,
            signing_ca=None):
        """
        Internal method called as a reference from the engine.vpn
        node
        """
        if signing_ca is None:
            signing_ca = VPNCertificateCA.objects.filter('Internal RSA').first()
        
        cert_auth = element_resolver(signing_ca)
        
        return ElementCreator(
            GatewayCertificate,
            exception=CertificateError,
            href=self.internal_gateway.get_relation('generate_certificate'),
            json={
                'common_name': common_name,
                'public_key_algorithm': public_key_algorithm,
                'signature_algorithm': signature_algorithm,
                'public_key_length': key_length,
                'certificate_authority_href': cert_auth})
    
    @property
    def certificate(self):
        return self.certificate_base64
    
    def renew(self):
        pass
    
    @property
    def expiration(self):
        pass
    
    def export_certificate(self):
        pass
        
        