""" License module handles operations for licensing and un-licensing engines """

from smc.elements.element import SMCElement
import smc.actions.search
import smc.api.common
import logging

logger = logging.getLogger(__name__)

class License(object):
    """
    Class to perform license based operations
    Bind will attach a license for an engine. It will first attempt to 'fetch' the
    license which auto maps based on the engine POS (for physical appliances). Otherwise
    it will fall back to finding an unassigned dynamic license and auto-assign.
    Unbind removes the license
    :param name: name of engine
    """
    def __init__(self, name):
        self.name = name
        self.links = []
        self.license_id = None
        self.element = None
        self.get_license_links()

    def bind(self):
        """
        Attempt to bind a license by calling fetch first, if the engine has
        a serial number mapped to license, SMC will auto-bind the right one.
        Otherwise try to find an available dynamic license and bind
        :return None
        """
        self.fetch()

        if not self.element.href: #if fetch fails, element.href = None
            logger.info("Could not fetch license, trying to get a dynamic license")

            for links in self.links:
                if links.get('rel') == 'bind':
                    self.element.href = links.get('href')

            self.get_dynamic_license()
            if self.license_id:
                self.element.json = {'license_id': self.license_id}
                smc.api.common._create(self.element)

    def unbind(self):
        """ 
        Unbind a license by device name 
        """
        for links in self.links:
            if links.get('rel') == 'unbind':
                self.element.href = links.get('href')
        smc.api.common._create(self.element)

    def fetch(self):
        """
        Fetch the license for the engine. If the engine has a mapped
        license by POS, it will be automatically assigned
        """
        for links in self.links:
            if links.get('rel') == 'fetch':
                self.element.href = links.get('href')
        smc.api.common._create(self.element)

    def get_license_links(self):
        """ 
        Get the needed href links based on the engine 
        """
        entry_json = smc.actions.search.element_as_json(self.name)

        if entry_json:
            self.element = SMCElement()
            self.element.name = self.name
            self.element.type = 'license'

            entry = entry_json.get('nodes')[0]
            for _, entries in entry.iteritems():
                for keys in entries:
                    if keys == 'link':
                        self.links = entries[keys]
                        break

    def get_dynamic_license(self):
        """
        Check for unbound dynamic licenses
        :return None
        """
        sys_license = smc.search.element_entry_point('licenses')
        licenses = smc.actions.search.element_by_href_as_json(sys_license)
        logger.debug("Searching for dynamic licenses in existing licenses: %s", licenses)

        license_id = None
        for _license in licenses.get('license'):
            if _license.get('bindings') == 'dynamic' and \
            _license.get('binding_state') == 'Unassigned':

                license_id = _license.get('license_id')
                logger.debug("Found a dynamic license; License_info: %s", license_id)
                break
        if license_id:
            self.license_id = license_id
        else:
            logger.error("No dynamic licenses were found. Cannot license security engine")
