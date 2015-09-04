import imp
from .base import Report,ModelReport,QuerySetReport,SQLReport,DateSQLReport

# TODO  make this seperate from vitalik's registry methods
_registry = {}

def register(klass):
    """
    Registers a Report Engine Report.  This gets the namespace and class's slug, puts them in a tuple, and stores the
    report, indexed by the namespace, slug tuple.

    :param klass: The class of the report to register.
    :return:
    """
    _registry[(klass.namespace,klass.slug)] = klass

def get_report(namespace,slug):
    """
    Fetches a report from the registry, by namespace and slug.

    :param namespace: The report namespace, a string.
    :param slug: The repot slug, a string
    :return: A subclass of reportengine.base.Report
    """
    try:
        return _registry[(namespace,slug)]
    except KeyError:
        raise Exception("No such report '%s'" % slug)

def all_reports():
    """
    Gets all reports from the registry

    :return:  A list of reports, subclasses of reportengine.base.Report
    """
    return _registry.items()

def autodiscover():
    """
    Looks for a file called 'reports.py' in your Django Application, then automatically imports that file, causing your
    reports to be loaded and registered.
    """
    from django.conf import settings
    REPORTING_SOURCE_FILE =  getattr(settings, 'REPORTING_SOURCE_FILE', 'reports') 
    for app in settings.INSTALLED_APPS:
        try:
            app_path = __import__(app, {}, {}, [app.split('.')[-1]]).__path__
        except AttributeError:
            continue

        try:
            imp.find_module(REPORTING_SOURCE_FILE, app_path)
        except ImportError:
            continue
        __import__('%s.%s' % (app, REPORTING_SOURCE_FILE))


