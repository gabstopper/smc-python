from smc.policy.policy import Policy
from smc.base.model import SubElement
from smc.base.collection import create_collection


class FileFilteringRule(SubElement):
    """
    Represents a file filtering rule
    """
    typeof = 'file_filtering_rule'

    def __init__(self, **meta):
        super(FileFilteringRule, self).__init__(**meta)
        pass

    def create(self):
        pass

    def add_after(self):
        pass

    def add_before(self):
        pass


class FileFilteringPolicy(Policy):
    """ 
    The File Filtering Policy references a specific file based policy for 
    doing additional inspection based on file types. Use the policy 
    parameters to specify how certain files are treated by either threat 
    intelligence feeds,sandbox or by local AV scanning. You can also use 
    this policy to disable threat prevention based on specific files.
    """
    typeof = 'file_filtering_policy'

    def __init__(self, name, **meta):
        super(FileFilteringPolicy, self).__init__(name, **meta)
        pass

    @classmethod
    def create(cls):
        pass

    @property
    def file_filtering_rules(self):
        """
        File filtering rules for this policy.

        :return: collection of :class:`.FileFilteringRule`
        :rtype: SubElementCollection
        """
        return create_collection(
            self.data.get_link('file_filtering_rules'),
            FileFilteringRule)

    def export(self): pass  # Not valid on file filtering policy
