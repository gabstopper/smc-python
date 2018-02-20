"""
.. versionadded:: 0.6.0
    Requires SMC version >= 6.3

Reports generated from the SMC. Provides an interface to running existing report
designs and exporting their contents.

Example usage::

    >>> from smc.administration.reports import ReportDesign, ReportTemplate, Report

List all available report templates::

    >>> list(ReportTemplate.objects.all())
    [ReportTemplate(name=Firewall Weekly Summary),
     ReportTemplate(name=Firewall Daily Summary from Specific Firewall),
     ReportTemplate(name=Firewall Multi-Link Usage)
     ...

Create a report design using an existing report template::

    >>> template = ReportTemplate('Firewall Weekly Summary')
    >>> template.create_design('myfirewallreport')
    ReportDesign(name=myfirewallreport)

Generate a report based on an existing or created report design::
        
    >>> list(ReportDesign.objects.all())
    [ReportDesign(name=Application and Web Security), ReportDesign(name=myfirewallreport)]
    ...
    >>> design = ReportDesign('Application and Web Security')
    >>> poller = design.generate(wait_for_finish=True)
    >>> while not poller.done():
    ...   poller.wait(3)
    ... 
    >>> poller.task.resource
    >>> Report(name=Application and Web Security #1515295820751)
    ...
    >>> design.report_files
    [Report(name=Application and Web Security #1515295820751), Report(name=Application and Web Security #1515360776422)]
    >>> report = Report('Application and Web Security #1515360776422')
    >>> print(report.creation_time)
    2018-01-07 15:32:56.422000
    >>> report.export_pdf(filename='/foo/bar/a.pdf')

"""
from smc.base.model import Element
from smc.administration.tasks import Task
from smc.base.util import datetime_from_ms, element_resolver
from smc.api.exceptions import CreateElementFailed


class ReportDesign(Element):
    """
    A ReportDesign defines a report available in the SMC. This class provides access
    to generating these reports and exporting into a format supported by the SMC.
    Example of generating a report, and providing a callback once the report is complete
    which exports the report::
    
        >>> def export_my_report(task):
        ...   if task.resource:
        ...     report = task.resource[0]
        ...     print("My report reference: %s" % report)
        ...     report.export_pdf('/Users/foo/myfile.pdf')
        ... 
        >>> 
        >>> report = ReportDesign('Application and Web Security')
        >>> poller = report.generate(wait_for_finish=True)
        >>> poller.add_done_callback(export_my_report)
        >>> while not poller.done():
        ...   poller.wait(3)
        ... 
        My report reference: Report(name=Application and Web Security #1515375369483)
    
    """
    typeof = 'report_design'
    
    def generate(self, start_time=0, end_time=0, 
            senders=None, wait_for_finish=False, timeout=5, **kw):  # @ReservedAssignment
        """
        Generate the report and optionally wait for results.
        You can optionally add filters to the report by providing the senders
        argument as a list of type Element::
        
            report = ReportDesign('Firewall Weekly Summary')
            begin = datetime_to_ms(datetime.strptime("2018-02-03T00:00:00", "%Y-%m-%dT%H:%M:%S"))
            end = datetime_to_ms(datetime.strptime("2018-02-04T00:00:00", "%Y-%m-%dT%H:%M:%S"))
            report.generate(start_time=begin, end_time=end, senders=[Engine('vm')])
        
        :param int period_begin: milliseconds time defining start time for report
        :param int period_end: milliseconds time defining end time for report
        :param senders: filter targets to use when generating report
        :type senders: list(Element)
        :param bool wait_for_finish: enable polling for results
        :param int timeout: timeout between polling
        :raises TaskRunFailed: refresh failed, possibly locked policy
        :rtype: TaskOperationPoller
        """
        if start_time and end_time:
            kw.setdefault('params', {}).update(
                {'start_time': start_time,
                 'end_time': end_time})
        if senders:
            kw.setdefault('json', {}).update({'senders': element_resolver(senders)})
        return Task.execute(self, 'generate',
            timeout=timeout, wait_for_finish=wait_for_finish, **kw)
    
    @property
    def report_files(self):
        """
        Retrieve all reports that are currently available on the SMC.
        
        :rtype: list(Report)
        """
        return [Report(**report) for report in self.make_request(
                resource='report_files')]
        

class ReportTemplate(Element):
    """
    A report template represents an existing template in the SMC. Templates can
    be retrieved through the normal collections::
    
        >>> list(ReportTemplate.objects.all())
        [ReportTemplate(name=Firewall Weekly Summary),
         ReportTemplate(name=Firewall Daily Summary from Specific Firewall),
         ReportTemplate(name=Firewall Multi-Link Usage)
         ...
    
    Once a report template of interest is identified, you can create a
    ReportDesign using that template::
    
        >>> template = ReportTemplate('Firewall Weekly Summary')
        >>> template.create_design('myfirewallreport')
        ReportDesign(name=myfirewallreport)
    """
    typeof = 'report_template'
    
    def create_design(self, name):
        """
        Create a report design based on an existing template.
        
        :param str name: Name of new report design
        :raises CreateElementFailed: failed to create template
        :rtype: ReportDesign
        """
        result = self.make_request(
            CreateElementFailed,
            resource='create_design',
            raw_result=True,
            method='create',
            params={'name': name})
    
        return ReportDesign(
            href=result.href, type=self.typeof, name=name)


class Report(Element):
    """
    Report represent a report that has been generated and that is
    currently stored on the SMC. These reports can be exported in multiple
    formats.
    """
    typeof = 'report_file'
    
    @property
    def creation_time(self):
        """
        When this report was generated. Using local time.
        
        :rtype: datetime.datetime
        """
        return datetime_from_ms(self.data.get('creation_time'))
    
    @property
    def period_begin(self):
        """
        Period when this report was specified to start.
        
        :rtype: datetime.datetime
        """
        return datetime_from_ms(self.data.get('period_begin'))
    
    @property
    def period_end(self):
        """
        Period when this report was specified to end.
        
        :rtype: datetime.datetime
        """
        return datetime_from_ms(self.data.get('period_end'))
    
    def export_pdf(self, filename):
        """
        Export the report in PDF format. Specify a path for which
        to save the file, including the trailing filename.
        
        :param str filename: path including filename
        :return: None
        """
        self.make_request(
            raw_result=True,
            resource='export',
            filename=filename, 
            headers = {'accept': 'application/pdf'})

    def export_text(self, filename=None):
        """
        Export in text format. Optionally provide a filename to
        save to.
        
        :param str filename: path including filename (optional)
        :return: None
        """
        result = self.make_request(
            resource='export',
            params={'format': 'txt'},
            filename=filename,
            raw_result=True, 
            headers = {'accept': 'text/plain'})

        if not filename:
            return result.content
