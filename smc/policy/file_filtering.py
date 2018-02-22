from smc.policy.policy import Policy
from smc.base.model import SubElement
from smc.base.collection import rule_collection
from smc.policy.rule import RuleCommon


class FileFilteringRule(RuleCommon, SubElement):
    """
    Represents a file filtering rule
    """
    typeof = 'file_filtering_rule'

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

    @classmethod
    def create(cls):
        pass

    @property
    def file_filtering_rules(self):
        """
        File filtering rules for this policy.

        :rtype: rule_collection(FileFilteringRule)
        """
        return rule_collection(
            self.get_relation('file_filtering_rules'),
            FileFilteringRule)

    def export(self): pass  # Not valid on file filtering policy
