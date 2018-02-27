"""
Engine feature add on functionality such as default NAT, Antivirus,
File Reputation, etc. These are common settings that are located under
the SMC AddOn or General properties.

Property features will have a common interface allowing you to `enable`,
`disable` and check `status` from the engine reference. When property
features are modified, they are done so against a local copy of the server
intsance. To commit the change, you must call .update() on the engine instance.

For example, to view status of antivirus, given a specific engine::

    engine.antivirus.status

Then enable or disable::

    engine.antivirus.enable()
    engine.antivirus.disable()
    engine.update()
   
..note:: Engine property settings require that you call engine.update() after
    making / queuing your changes.
"""
from smc.base.model import Element
from smc.base.structs import NestedDict
from smc.elements.profiles import SandboxService
from smc.base.util import element_resolver


def get_proxy(http_proxy):
    if http_proxy:
        proxies = [element_resolver(proxy) for proxy in http_proxy]
    else: 
        proxies = []
    return proxies


class AntiVirus(NestedDict):
    """
    Antivirus settings for the engine. In order to use AV,
    you must also have DNS server addresses configured on
    the engine.
    
    Enable AV, use a proxy for updates and adjust update
    schedule::
    
        engine.antivirus.enable()
        engine.antivirus.update_frequency('daily')
        engine.antivirus.update_day('tu')
        engine.antivirus.log_level('transient')
        engine.antivirus.http_proxy('10.0.0.1', proxy_port=8080, user='foo', password='password')
        engine.update()
    
    :ivar bool antivirus_enabled: is antivirus enabled
    :ivar str antivirus_http_proxy: http proxy settings
    :ivar bool antivirus_http_proxy_enabled: is http proxy enabled
    :ivar int antivirus_proxy_port: http proxy port
    :ivar str antivirus_proxy_user: http proxy user
    :ivar str antivirus_update: how often to update
    :ivar str antivirus_update_day: if update set to weekly, which day to update
    :ivar int antivirus_update_time: time to update av signatures
    :ivar str virus_log_level: antivirus logging level

    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        av = engine.data.get('antivirus', {})
        super(AntiVirus, self).__init__(data=av)
    
    def update_frequency(self, when):
        """
        Set the update frequency. By default this is daily.
        
        :param str antivirus_update: how often to check for updates. Valid options
            are: 'never','1hour', 'startup', 'daily', 'weekly'
        """
        if when in ('never', '1hour', 'startup', 'daily', 'weekly'):
            self.update(antivirus_update=when)
    
    def update_day(self, day):
        """
        Update the day when updates should occur.
        
        :param str day: only used if 'weekly' is specified. Which day
            or week to perform update. Valid options: mo, tu, we, th,
            fr, sa, su.
        """
        if day in ('mo','tu','we','th','fr','sa','su'):
            self.update(antivirus_update_day=day)
    
    def log_level(self, level):
        """
        Set the log level for antivirus alerting.
        
        :param str log_level: none,transient,stored,essential,alert
        """
        if level in ('none', 'transient', 'stored' ,'essential','alert'):
            self.update(virus_log_level=level)
          
    def http_proxy(self, proxy, proxy_port, user=None, password=None):
        """
        .. versionadded:: 0.5.7
            Requires SMC and engine version >= 6.4
        
        Set http proxy settings for Antivirus updates.
        
        :param str proxy: proxy IP address
        :param str,int proxy_port: proxy port
        :param str user: optional user for authentication
        """
        self.update(
            antivirus_http_proxy=proxy,
            antivirus_proxy_port=proxy_port,
            antivirus_proxy_user=user if user else '',
            antivirus_proxy_password=password if password else '',
            antivirus_http_proxy_enabled=True)
    
    def disable(self):
        """
        Disable antivirus on the engine
        """
        self.update(antivirus_enabled=False)
    
    @property
    def status(self):
        """
        Status of AV on this engine
        
        :rtype: bool
        """
        return self.get('antivirus_enabled', False)
    
    def enable(self):
        """
        Enable antivirus on the engine
        """
        self.update(antivirus_enabled=True,
                    virus_mirror='update.nai.com/Products/CommonUpdater' if \
                        not self.get('virus_mirror') else self.virus_mirror,
                    antivirus_update_time=self.antivirus_update_time if \
                        self.get('antivirus_update_time') else 21600000)
        
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class FileReputation(NestedDict):
    """
    Configure the engine to use File Reputation capabilities.
    
    Enable file reputation and specify outbound http proxies for
    queries::
    
        engine.file_reputation.enable(http_proxy=[HttpProxy('myproxy')])
        engine.update()
    
    :ivar str file_reputation_context: file reputation context, either
        gti_cloud_only or disabled
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        gti = engine.data.get('gti_settings', {})
        super(FileReputation, self).__init__(data=gti)
    
    def disable(self):
        """
        Disable any file reputation on the engine.
        """
        self.update(file_reputation_context='disabled')
    
    @property
    def status(self):
        """
        Return the status of File Reputation on this engine.
        
        :rtype: bool
        """
        if self.file_reputation_context == 'disabled':
            return False
        return True
    
    @property
    def http_proxy(self):
        """    
        Return any HTTP Proxies that are configured for File 
        Reputation.
        
        :return: list of http proxy instances
        :rtype: list(HttpProxy)
        """
        return [Element.from_href(proxy) for proxy in self.get('http_proxy')]
        
    def enable(self, http_proxy=None):
        """
        Enable GTI reputation on the engine. If proxy servers
        are needed, provide a list of proxy elements.
        
        :param http_proxy: list of proxies for GTI connections
        :type http_proxy: list(str,HttpProxy)
        """
        self.update(file_reputation_context='gti_cloud_only',
                    http_proxy=get_proxy(http_proxy))
        
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class SidewinderProxy(object):
    """
    Sidewinder status on this engine. Sidewinder proxy can only be
    enabled on specific engine types and also requires SMC and
    engine version >= 6.1.
    
    Enable Sidewinder proxy::
    
        engine.sidewinder_proxy.enable()
        
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine
        
    def enable(self):
        """
        Enable Sidewinder proxy on the engine
        """
        self.engine.data['sidewinder_proxy_enabled'] = True
    
    def disable(self):
        """
        Disable Sidewinder proxy on the engine
        """
        self.engine.data['sidewinder_proxy_enabled'] = False
    
    @property
    def status(self):
        """
        Status of Sidewinder proxy on this engine
        
        :rtype: bool
        """
        return self.engine.data['sidewinder_proxy_enabled']
    
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)
    

class UrlFiltering(NestedDict):
    """
    Enable URL Filtering on the engine.
    
    Enable Url Filtering with next hop proxies::
    
        engine.url_filtering.enable(http_proxy=[HttpProxy('myproxy')])
        engine.update()
    
    Disable Url Filtering::

        engine.url_filtering.disable()
        engine.update()
        
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        ts = engine.data.get('ts_settings', {})
        super(UrlFiltering, self).__init__(data=ts)
    
    @property
    def http_proxy(self):
        """    
        Return any HTTP Proxies that are configured for Url
        Filtering.
        
        :return: list of http proxy instances
        :rtype: list(HttpProxy)
        """
        return [Element.from_href(proxy) for proxy in self.get('http_proxy')]

    def enable(self, http_proxy=None):
        """
        Enable URL Filtering on the engine. If proxy servers
        are needed, provide a list of HTTPProxy elements.
        
        :param http_proxy: list of proxies for GTI connections
        :type http_proxy: list(str,HttpProxy)
        """
        self.update(ts_enabled=True, http_proxy=get_proxy(http_proxy))
    
    def disable(self):
        """
        Disable URL Filtering on the engine
        """
        self.update(ts_enabled=False)
    
    @property
    def status(self):
        """
        Return the status of URL Filtering on the engine
        
        :rtype: bool
        """
        return self.get('ts_enabled', False)
    
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)
    

class Sandbox(NestedDict):
    """
    Engine based sandbox settings. Sandbox can be configured for
    local (on prem) or cloud based sandbox. To create file filtering
    policies that use sandbox, you must first enable it and
    provide license keys on the engine.
    
    Enable cloud sandbox on the engine, specifying a proxy for outbound
    connections::
    
        engine.sandbox.enable(
            license_key='123',
            license_token='456',
            http_proxy=[HttpProxy('myproxy')])
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine
        sb = engine.data.get('sandbox_settings', {})
        super(Sandbox, self).__init__(data=sb)
            
    @property
    def status(self):
        """
        Status of sandbox on this engine
        
        :rtype: bool
        """
        if 'sandbox_type' in self.engine.data:
            if self.engine.sandbox_type == 'none':
                return False
            return True
        return False  # Tmp, attribute missing on newly created engines
    
    def disable(self):
        """
        Disable the sandbox on this engine.
        """
        self.engine.data.update(sandbox_type='none')
        self.pop('cloud_sandbox_settings', None) #pre-6.3
        self.pop('sandbox_settings', None)
    
    def enable(self, license_key, license_token,
               sandbox_type='cloud_sandbox', service='US Data Centers',
               http_proxy=None):
        """
        Enable sandbox on this engine. Provide a valid license key
        and license token obtained from your engine licensing.
        Requires SMC version >= 6.3.
        
        .. note:: Cloud sandbox is a feature that requires an engine license.

        :param str license_key: license key for specific engine
        :param str license_token: license token for specific engine
        :param str sandbox_type: 'local_sandbox' or 'cloud_sandbox'
        :param str,SandboxService service: a sandbox service element from SMC. The service
            defines which location the engine is in and which data centers to use.
            The default is to use the 'US Data Centers' profile if undefined.
        :return: None
        """
        service = element_resolver(SandboxService(service))
            
        self.update(sandbox_license_key=license_key,
                    sandbox_license_token=license_token,
                    sandbox_service=service,
                    http_proxy=get_proxy(http_proxy))
        
        self.engine.data.setdefault('sandbox_settings', {}).update(self.data)
        self.engine.data.update(sandbox_type=sandbox_type)
    
    @property
    def http_proxy(self):
        """    
        Return any HTTP Proxies that are configured for Sandbox.
        
        :return: list of http proxy instances
        :rtype: list(HttpProxy)
        """
        return [Element.from_href(proxy) for proxy in self.get('http_proxy')]
            
    def __repr__(self):
        return '{0}(enabled={1})'.format(
            self.__class__.__name__, self.status)


class TLSInspection(object):
    """
    TLS Inspection settings control settings for doing inbound
    TLS decryption and outbound client TLS decryption. This
    provides an interface to manage TLSServerCredentials and
    TLSClientCredentials assigned to the engine.
    
    .. note:: You must call engine.update() to commit any changes.
    """
    def __init__(self, engine):
        self.engine = engine
        
    @property
    def server_credentials(self):
        """
        Return a list of assigned (if any) TLSServerCredentials
        assigned to this engine.
        
        :rtype: list(TLSServerCredential)
        """
        return [Element.from_href(credential)
                for credential in self.engine.server_credential]
    
    def add_tls_credential(self, credentials):
        """        
        Add a list of TLSServerCredential to this engine.
        TLSServerCredentials can be in element form or can also
        be the href for the element.
        
        :param credentials: list of pre-created TLSServerCredentials
        :type credentials: list(str,TLSServerCredential)
        :return: None
        """
        for cred in credentials:
            href = element_resolver(cred)
            if href not in self.engine.server_credential:
                self.engine.server_credential.append(href)
    
    def remove_tls_credential(self, credentials):
        """    
        Remove a list of TLSServerCredentials on this engine.
        
        :param credentials: list of credentials to remove from the
            engine
        :type credentials: list(str,TLSServerCredential)
        :return: None
        """
        for cred in credentials:
            href = element_resolver(cred)
            if href in self.engine.server_credential:
                self.engine.server_credential.remove(href)
      

'''
class ClientInspection(object):
    def __init__(self, engine):
        self.engine = engine
    
    @property
    def status(self):
        """
        Whether client based decryption is enabled or disabled.
        
        :rtype: bool
        """
        return getattr(self.engine, 'tls_client_protection', False)
    
    def enable(self, client_protection_ca):
        """
        Enable client decryption. Provide a valid client protection
        CA that the engine will use to decrypt.
        
        :param str,ClientProtectionCA client_protection_ca: href or
            element
        :return: None
        """
        self.engine.data.update(tls_client_protection=
            [{'ca_for_signing_ref': element_resolver(client_protection_ca)}])
    
    def disable(self):
        pass
        
    @property
    def client_protection_ca(self):
        """
        Return the Client Protection Certificate Authority assigned
        to this engine. The CA is used to provide decryption services
        to outbound client connections.
        
        :rtype: ClientProtectionCA
        """
        return Element.from_href(
            self.engine.tls_client_protection)
'''
