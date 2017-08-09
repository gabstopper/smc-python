"""
Module representing read-only licenses in SMC
"""
class Licenses(object):
    """
    List of all available licenses for this Management Server.
    """
    def __init__(self, licenses):
        self.licenses = []
        for lic in licenses['license']:
            self.licenses.append(License(**lic))
    
    def __iter__(self):
        return iter(self.licenses)
    
    def __len__(self):
        return len(self.licenses)
    
    def __getitem__(self, index):
        return self.licenses[index]


class License(object):
    """
    Valid attributes (read-only) are:

    :ivar binding: master license binding serial number
    :ivar binding_state: state of license, unassigned, bound, etc
    :ivar bindings: which node is the license bound to
    :ivar customer_name: customer name, if any
    :ivar enabled_feature_packs: additional feature licenses
    :ivar expiration_date: when license expires
    :ivar features: features enabled on this license
    :ivar granted_date: when license date began
    :ivar license_id: license ID (unique for each license)
    :ivar license_version: max version for this license
    :ivar maintenance_contract_expires_date: date/time support ends
    :ivar management_server_binding: management server binding POS
    :ivar proof_of_license: proof of license key
    :ivar type: type of license (SECNODE, Mgmt, etc)
    """
    typeof = 'licenses'

    def __init__(self, **data):
        for d, v in data.items():
            setattr(self, d, v)

    @property
    def name(self):
        return self.license_id

    def __getattr__(self, attr):
        return None
    
    def __repr__(self):
        return '{0}(id={1},binding={2},bound_to={3})'.format(
            self.__class__.__name__,
            self.name,
            self.binding_state,
            self.bound_to)
