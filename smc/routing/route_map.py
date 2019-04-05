"""
Route map rules and match condition elements for dynamic routing policies.

A RouteMap can be created and subsequent rules can be inserted
within the route map policy. 

A MatchCondition is the subject of the rule providing criteria to
specify how a match is made. Elements used in match conditions are
`next_hop`, `peer_address`, `access_list` and type `metric`.

.. seealso:: :class:`~MatchCondition` for more details on how to add match
    conditions to a rule or modify an existing rule.

Example of creating a RouteMap and subsequent rule, specifying match condition
options as keyword arguments::

    >>> from smc.routing.route_map import RouteMap
    >>> from smc.routing.access_list import IPAccessList
    >>> from smc.routing.bgp import ExternalBGPPeer
    ...
    >>> rm = RouteMap.create(name='myroutemap')
    >>> rm
    RouteMap(name=myroutemap)
    >>> rm.route_map_rules.create(name='rule1', action='permit',
            next_hop=IPAccessList('myacl'), peer_address=ExternalBGPPeer('bgppeer'),
            metric=20)
    RouteMapRule(name=rule1)
    ...
    >>> rule1 = rm.route_map_rules.get(0) # retrieve rule 1 from the route map
    >>> for condition in rule1.match_condition:
    ...   condition
    ... 
    Condition(rank=1, element=ExternalBGPPeer(name=bgppeer), type=u'peer_address')
    Condition(rank=2, element=IPAccessList(name=myacl), type='access_list')
    Condition(rank=3, element=Metric(value=20), type=u'metric')

Instead of providing singular match condition keywords to the `create` constructor,
you can also optionally provide a MatchCondition instance when creating a rule::

    >>> from smc.routing.route_map import MatchCondition
    >>> condition = MatchCondition()
    >>> condition.add_access_list(IPAccessList('myacl'))
    >>> condition.add_peer_address(ExternalBGPPeer('bgppeer'))
    >>> condition.add_metric(20)
    >>> condition
    MatchCondition(entries=3)
    >>> rm.route_map_rules.create(
    ...         name='foo2',
    ...         finish=False,
    ...         match_condition=condition)
    RouteMapRule(name=foo2)

To remove a match condition, first obtain it's rank. After making the modification
be sure to call update on the rule element::

    >>> rule = rm.route_map_rules.get(0)
    >>> rule.match_condition.remove_condition(rank=2)
    >>> rule.update()

You can also delete a rule by obtaining the rule, either through the
route_map_rules collection reference or by iteration::

    rule = rm.route_map_rules.get(1)
    rule.delete()
    
Or by the name::

    rule = rm.route_map_rules.get_exact('foo')
    rule.delete()

.. seealso:: :class:`smc.base.collection.rule_collection`
"""
import collections
from smc.base.model import Element, ElementCreator, SubElement
from smc.base.collection import rule_collection
from smc.policy.rule import RuleCommon
from smc.api.exceptions import CreateRuleFailed


Metric = collections.namedtuple('Metric', 'value')
"""
A metric is a simple namedtuple for returning a Metric route map
element

:ivar int value: metric value for this BGP route
"""


Condition = collections.namedtuple('Condition', 'rank element type')
"""
A condition defines the type of dynamic element that is used in
the match condition field of a route map.

:ivar str rank: the rank in the match condition list
:ivar str element: the dynamic element type for this condition
:ivar str type: type defines the type of entry, i.e. metric, peer_address, next_hop,
    access_list
"""


class MatchCondition(object):
    """
    MatchCondition is an iterable container class that holds the
    match conditions for the route map rule. The list of conditions
    are ranked in order. You can add, remove and view conditions currently
    configured in this rule. After making modifications, call update on
    the rule to commit back to SMC.
    
    When iterating over a match condition, a namedtuple is returned that
    provides the rank and element type for the condition. It is then possible
    to add by rank (ie: insert conditions in between others), or remove based
    on rank. If not rank is provided when adding new conditions, the
    condition is added to the bottom of the rank list.
    
    :rtype: list(Condition)
    """
    def __init__(self, rule=None):
        self.conditions = rule.data.get(
            'match_condition', []) if rule else []

    def __iter__(self):
        for condition in self.conditions:
            condition_type = condition.get('type')
            if 'element' in condition_type:
                entry = Element.from_href(
                    condition.get('access_list_ref'))
                condition_type = 'access_list'
            elif 'metric' in condition_type:
                entry = Metric(
                    condition.get('metric'))
            elif 'peer_address' in condition_type:
                ref = 'fwcluster_peer_address_ref' if 'fwcluster_peer_address_ref'\
                    in condition else 'external_bgp_peer_address_ref'
                entry = Element.from_href(
                    condition.get(ref))
            elif 'next_hop' in condition_type:
                entry = Element.from_href(
                    condition.get('next_hop_ref'))

            yield Condition(condition.get('rank'), entry, condition_type)
    
    def add_access_list(self, accesslist, rank=None):
        """
        Add an access list to the match condition. Valid
        access list types are IPAccessList (v4 and v6),
        IPPrefixList (v4 and v6), AS Path, CommunityAccessList,
        ExtendedCommunityAccessList.
        """
        self.conditions.append(
            dict(access_list_ref=accesslist.href,
                 type='element',
                 rank=rank))
    
    def add_metric(self, value, rank=None):
        """
        Add a metric to this match condition
        
        :param int value: metric value
        """
        self.conditions.append(
            dict(metric=value, type='metric', rank=rank))
    
    def add_next_hop(self, access_or_prefix_list, rank=None):
        """
        Add a next hop condition. Next hop elements must be
        of type IPAccessList or IPPrefixList.
        
        :raises ElementNotFound: If element specified does not exist
        """
        self.conditions.append(dict(
            next_hop_ref=access_or_prefix_list.href,
            type='next_hop',
            rank=rank))
    
    def add_peer_address(self, ext_bgp_peer_or_fw, rank=None):
        """
        Add a peer address. Peer address types are ExternalBGPPeer
        or Engine.
        
        :raises ElementNotFound: If element specified does not exist
        """
        if ext_bgp_peer_or_fw.typeof == 'external_bgp_peer':
            ref = 'external_bgp_peer_address_ref'
        else: # engine
            ref = 'fwcluster_peer_address_ref'
        self.conditions.append(
            {ref: ext_bgp_peer_or_fw.href,
             'rank': rank,
             'type': 'peer_address'})
    
    def remove_condition(self, rank):
        """
        Remove a condition element using it's rank. You can find the
        rank and element for a match condition by iterating the match
        condition::
        
            >>> rule1 = rm.route_map_rules.get(0)
            >>> for condition in rule1.match_condition:
            ...   condition
            ... 
            Condition(rank=1, element=ExternalBGPPeer(name=bgppeer))
            Condition(rank=2, element=IPAccessList(name=myacl))
            Condition(rank=3, element=Metric(value=20))
        
        Then delete by rank. Call update on the rule after making the
        modification.
        
        :param int rank: rank of the condition to remove
        :raises UpdateElementFailed: failed to update rule
        :return: None
        """
        self.conditions[:] = [r for r in self.conditions
            if r.get('rank') != rank]
    
    def __repr__(self):
        return 'MatchCondition(entries={})'.format(
            len(self.conditions))

           
class RouteMapRule(RuleCommon, SubElement):
    """
    A route map rule represents the rules to be processed for a route
    map assigned to a specific BGP network. A match condition can be
    provided which encapsulates using dynamic routing element types
    such as IPAccessList, IPPrefixList, etc.
    """
    typeof = 'route_map_rule'
    
    def create(self, name, action='permit', goto=None, finish=False,
               call=None, comment=None, add_pos=None, after=None,
               before=None, **match_condition):
        """
        Create a route map rule. You can provide match conditions
        by using keyword arguments specifying the required types.
        You can also create the route map rule and add match conditions
        after.
        
        :param str name: name for this rule
        :param str action: permit or deny
        :param str goto: specify a rule section to goto after if there
            is a match condition. This will override the finish parameter
        :param bool finish: finish stops the processing after a match condition.
            If finish is False, processing will continue to the next rule.
        :param RouteMap call: call another route map after matching. 
        :param str comment: optional comment for the rule
        :param int add_pos: position to insert the rule, starting with position 1. If
            the position value is greater than the number of rules, the rule is inserted at
            the bottom. If add_pos is not provided, rule is inserted in position 1. Mutually
            exclusive with ``after`` and ``before`` params.
        :param str after: Rule tag to add this rule after. Mutually exclusive with ``add_pos``
            and ``before`` params.
        :param str before: Rule tag to add this rule before. Mutually exclusive with ``add_pos``
            and ``after`` params.
        :param match_condition: keyword values identifying initial
            values for the match condition. Valid keyword arguments
            are 'access_list', 'next_hop', 'metric' and 'peer_address'.
            You can also optionally pass the keyword 'match_condition'
            with an instance of MatchCondition.
        :raises CreateRuleFailed: failure to insert rule with reason
        :raises ElementNotFound: if references elements in a match condition
            this can be raised when the element specified is not found.
        
        .. seealso:: :class:`~MatchCondition` for valid elements and
            expected values for each type.
        """
        json = {'name': name,
                'action': action,
                'finish': finish,
                'goto': goto.href if goto else None,
                'call_route_map_ref': None if not call else call.href,
                'comment': comment}
        
        if not match_condition:
            json.update(match_condition=[])
        else:
            if 'match_condition' in match_condition:
                conditions = match_condition.pop('match_condition')
            else:
                conditions = MatchCondition()
                if 'peer_address' in match_condition:
                    conditions.add_peer_address(
                        match_condition.pop('peer_address'))
                if 'next_hop' in match_condition:
                    conditions.add_next_hop(
                        match_condition.pop('next_hop'))
                if 'metric' in match_condition:
                    conditions.add_metric(
                        match_condition.pop('metric'))
                if 'access_list' in match_condition:
                    conditions.add_access_list(
                        match_condition.pop('access_list'))
            
            json.update(match_condition=conditions.conditions)
        
        params = None
        href = self.href 
        if add_pos is not None: 
            href = self.add_at_position(add_pos) 
        elif before or after: 
            params = self.add_before_after(before, after)
        
        return ElementCreator(
            self.__class__,
            exception=CreateRuleFailed, 
            href=href,
            params=params, 
            json=json)

    @property
    def comment(self):
        """
        Get and set the comment for this rule.
        
        :param str value: string comment
        :rtype: str
        """
        return self.data.get('comment')
    
    @comment.setter
    def comment(self, value):
        self.data['comment'] = value
        
    @property
    def goto(self):
        """
        If the rule is set to goto a rule section, return
        the rule section, otherwise it will return None.
        Check the value of finish to determine if the rule
        is set to finish on match.
        
        :return: RouteMap or None
        """
        return Element.from_href(
            self.data.get('goto'))
    
    def goto_rule_section(self, rule_section):
        """
        Set this rule to goto a specific rule section after
        match. If goto is None, then check value of finish.
        
        :param RouteMapRule rule_section: pass rule section
        :return: None
        """
        self.data.update(goto=rule_section.href)
        
    @property
    def action(self):
        """
        Action for this route map rule. Valid actions
        are 'permit' and 'deny'.
        
        :rtype: str
        """
        return self.data.get('action')
    
    @property
    def finish(self):
        """
        Is rule action goto set to finish on this rule match.
        If finish is False, then the policy will proceed to
        the next rule.
        
        :rtype: bool
        """
        return self.data.get('finish')
    
    @property
    def is_disabled(self):
        """
        Is the rule disabled
        
        :rtype: bool
        """
        return self.data.get('is_disabled')
    
    @property
    def is_rule_section(self):
        return 'match_condition' not in self.data
    
    def call_route_map(self, route_map):
        """
        Call another route map after match of this rule.
        Call update on the rule to save after modification.
        
        :param RouteMap route_map: Pass the route map element
        :raises ElementNotFound: invalid RouteMap reference passed
        :return: None
        """
        self.data.update(call_route_map_ref=route_map.href)
    
    @property
    def match_condition(self):
        """
        Return the match condition for this rule. This
        can then be modified in place. Be sure to call
        update on the rule to save.
        
        :rtype: MatchCondition
        """
        return MatchCondition(self)
    

class RouteMap(Element):
    """
    Use Route Map elements in more complex networks to control or manipulate
    routes. You can use Access List elements as a Matching Condition in a
    Route Map rule.
    RouteMaps are rule lists similar to normal policies and can be iterated::
    
        >>> from smc.routing.route_map import RouteMap
        >>> rm = RouteMap('myroutemap')
        >>> for rule in rm.route_map_rules:
        ...   rule
        ... 
        RouteMapRule(name=Rule @115.13)
        RouteMapRule(name=Rule @117.0)
        
    """
    typeof = 'route_map'
    
    @classmethod
    def create(cls, name, comment=None):
        """
        Create a new route map. After creation, you can add a rule
        and subsequent match conditions.
        
        :param str name: name of route map
        :param str comment: optional comment
        :raises CreateElementFailed: failed creating route map
        :rtype: RouteMap
        """
        json = {'name': name,
                'comment': comment}

        return ElementCreator(cls, json)
    
    @property
    def route_map_rules(self):
        """ 
        IPv6NAT Rule entry point 

        :rtype: rule_collection(IPv6NATRule) 
        """ 
        return rule_collection( 
            self.get_relation('route_map_rules'), RouteMapRule)
    
    def search_rule(self, search):
        """
        Search the RouteMap policy using a search string
        
        :param str search: search string for a contains match against
            the rule name and comments field
        :rtype: list(RouteMapRule)
        """
        return [RouteMapRule(**rule) for rule in self.make_request( 
            resource='search_rule', params={'filter': search})]
