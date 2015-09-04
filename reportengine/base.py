"""
Reports base classes. This reports module tries to provide an ORM agnostic reports engine that will allow nice reports
to be generated and exportable in a variety of formats. It seeks to be easy to use with query sets, raw SQL, or pure
python. An additional goal is to have the reports be managed by model instances as well (e.g. a generic SQL based
report that can be done in the backend).
"""
from django import forms
from django.db.models.fields.related import RelatedField
from .filtercontrols import *
from .outputformats import *
import datetime

# Pulled from vitalik's Django-reporting
def get_model_field(model, name):
    """
    Gets a field from a Django model.

    :param model: A Django model, this should be the class itself.
    :param name:  A Django model's field.
    :return:  The field from the model, a subclass of django.db.models.Model
    """
    return model._meta.get_field(name)

# Based on vitalik's Django-reporting
def get_lookup_field(model, original, lookup):
    """
    Gets a lookup field from a django model, this recursively follows relations
    that are indicated by Django's __ notation.

    If there were a model like Customer -> Address -> Street (where even street is a model),
    calling get_lookup_field(Customer, "address__street__line1") would return
    (line1 (a CharField), and Street (a subclass of Model))

    :param model: A django model, this should be the actual Model class.
    :param original:  A django model, this should be the initial model class.
                      It seems this is not used by the function.
    :param lookup: The django lookup string, delimited by __
    :return:  A tuple of (field, model) where model is a subclass of django.db.models.Model and field is a
              subclass of django.db.models.fields.Field
    """
    parts = lookup.split('__')
    field = get_model_field(model, parts[0])
    if not isinstance(field, RelatedField) or len(parts) == 1:
        return field,model
    rel_model = field.rel.to
    next_lookup = '__'.join(parts[1:])
    return get_lookup_field(rel_model, original, next_lookup)

class Report(object):
    """
    An abstract reportengine report.  Concrete report types inherit from this.  Override get_rows to make this concrete.

    For Example::

            class MyReport(Report):
                def get_rows(self, *args, **kwargs):
                    return [(x,x*10) for x in range(0,100)], (('total', 100),)
    """
    verbose_name="Abstract Report"
    namespace = "Default"
    slug ="base"
    labels = None
    per_page=100
    can_show_all=True
    output_formats=[AdminOutputFormat(),CSVOutputFormat()]
    if XLS_AVAILABLE:
        output_formats.append(XLSOutputFormat())
    allow_unspecified_filters = False
    date_field = None  # if specified will lookup for this date field. .this is currently limited to queryset based lookups
    default_mask = {}  # a dict of filter default values. Can be callable

    # TODO add charts = [ {'name','type e.g. bar','data':(0,1,3) cols in table}]
    # then i can auto embed the charts at the top of the report based upon that data..

    def get_default_mask(self):
        """
           Builds default mask. The filter is merged with this to create the filter for the report. Items can be
           callable and will be resolved when called here (which should be at view time).
         
           :return: a dictionary of filter key/value pairs
        """
        m={}
        for k in self.default_mask.keys():
            v=self.default_mask[k]
            m[k] =  callable(v) and v() or v
        return m

    def get_filter_form(self, data):
        """
        Returns a form with data.

        :param data: Should be a dictionary, with filter data in it.
        :return:  A form that is ready for validation.
        """
        form = forms.Form(data=data)
        return form

    # CONSIDER maybe an "update rows"?
    # CONSIDER should the resultant rows be a generator instead of a list?
    # CONSIDER should paging be dealt with here to more intelligently handle aggregates?
    def get_rows(self,filters={},order_by=None):
        """
        Given filter parameters and an order by field, this returns the actual rows of the report.

        :param filters: The parameters by which this report should be filtered.
        :param order_by:  The field by which this report should be ordered.
        :return:  A tuple (resultant rows, metadata)
        """
        raise NotImplementedError("Subclass should return ([],('total',0),)")


    # CONSIDER do this by day or by month? month seems most efficient in terms of optimizing queries
    # CONSIDER - should this be removed from the API?  Is it implemented by any subclasses?
    def get_monthly_aggregates(self,year,month):
        """Called when assembling a calendar view of reports. This will be queried for every day, so must be quick"""
        # CONSIDER worry about timezone? or just assume Django has this covered?
        raise NotImplementedError("Still an idea in the works")

class QuerySetReport(Report):
    """
    A report that is based on a Django ORM Queryset.
    """
    # TODO make labels more addressable. now fixed to fields in model. what happens with relations?
    labels = None
    queryset = None
    """
    list_filter must contain either ModelFields or FilterControls
    """
    list_filter = []

    def get_filter_form(self, data):
        """
        get_filter_form constructs a filter form, with the appropriate filtercontrol fields, based on the data passed.

        If the item in list_filter is a FilterControl, then the control will be added to the form filters.

        If the item in list_filter is a field lookup string, then a pre-registered filtercontrol corresponding to that field
        may be added to the form filters.

        This will follow __ relations (see get_lookup_field docs above)

        :param data: A dictionary of filter fields.
        :return:  A form with the filtered fields.
        """
        # NOTE - get_lookup_field does follow __ relations, so not sure about the above comment.
        # TODO iterate through list filter and create appropriate widget and prefill from request
        form = forms.Form(data=data)
        for f in self.list_filter:
            # Allow specification of custom filter control, or specify field name (and label?)
            if isinstance(f,FilterControl):
                control=f
            else:
                mfi,mfm=get_lookup_field(self.queryset.model,self.queryset.model,f)
                # TODO allow label as param 2
                control = FilterControl.create_from_modelfield(mfi,f)
            if control:
                fields = control.get_fields()
                form.fields.update(fields)
        form.full_clean()
        return form
    
    def get_queryset(self, filters, order_by, queryset=None):
        """
        Given filters, an order_by and an optional query set, this returns a queryset for this report.  Override this
        to change the querysets in your reports.

        :param filters:   A dictionary of field/value pairs that the report can be filtered on.
        :param order_by:  The field or statement by which this queryset should be ordered.
        :param queryset:  An optional queryset.  If None, self.queryset will be used.
        :return:  A filtered and ordered queryset.
        """
        if queryset is None:
            queryset = self.queryset
        queryset = queryset.filter(**filters)
        if order_by:
            queryset = queryset.order_by(order_by)
        return queryset

    def get_rows(self,filters={},order_by=None):
        """
        Given the rows and order_by value, this returns the actual report tuple.  This needn't be overriden by
        subclasses unless special functionality is needed.  Instead, consider overriding `get_queryset.`

        :param filters:   A dictionary of field/value pairs that the report can be filtered on.
        :param order_by:  The field or statement by which this queryset should be ordered.

        :return:  A tuple of rows and metadata.
        """
        qs = self.get_queryset(filters, order_by)
        return qs.values_list(*self.labels),(("total",qs.count()),)

class ModelReport(QuerySetReport):
    """
    A report on a specific django model.  Subclasses must define `model` on the class.
    """
    model = None

    def __init__(self):
        """
        Instantiate the ModelReport
        """
        super(ModelReport, self).__init__()
        self.queryset = self.model.objects.all()

    def get_queryset(self, filters, order_by, queryset=None):
        """
        Gets a report based on the Model's fields, given filters, an order by, and an optional queryset.

        :param filters:  The dictionary of filters with which to filter this model report.
        :param order_by: The field by which this report will be ordered.
        :param queryset: An optional queryset.  If none, this will use a queryset that gets all instances of
                         the given model.

        :return:  A filtered queryset.
        """
        if queryset is None and self.queryset is None:
            queryset = self.model.objects.all()
        return super(ModelReport, self).get_queryset(filters, order_by, queryset)

class SQLReport(Report):
    """
    A subclass of Report, used with raw SQL.
    """
    row_sql=None # sql statement with named  parameters in python syntax (e.g. "%(age)s" )
    aggregate_sql=None # sql statement that brings in aggregates. pulls from column name and value for first row only
    query_params=[] # list of tuples, (name,label,datatype) where datatype is a mapping to a registerd filtercontrol

    #TODO this should be _private.
    def get_connection(self):
        """
        Gets the django database connection.

        :return:  The database connection.
        """
        from django.db import connection
        return connection

    #TODO this should be _private.
    def get_cursor(self):
        """
        Gets the cursor for the connection.

        :return: Database connection cursor
        """
        return self.get_connection().cursor()

    #TODO use string formatting instead of older python replacement
    def get_row_sql(self, filters, order_by):
        """
        This applies filters directly to the SQL string, which should contain python keyed strings.

        :param filters:  A dictionary of filters to apply to this sql.
        :param order_by: This is ignored, but may be used by subclasses.
        :return:  The text-replaced SQL, or none if self.row_sql doesn't exist.
        """
        if self.row_sql:
            return self.row_sql % filters
        return None
    
    def get_aggregate_sql(self, filters):
        """
        This applies filters to the aggregate SQL.

        :param filters: A dictoinary of filters to apply to the sql.
        :return:  The text-replaced SQL or None if self.aggregate_sql doesn't exist.
        """
        if self.aggregate_sql:
            return self.aggregate_sql % filters
        return None

    #TODO make this _private.
    #TODO Instead of fetchall, use a generator.
    def get_row_data(self, filters, order_by):
        """
        Returns the cursor based on a filter dictionary.

        :param filters:  A dictionary of field->value filters to filter the report.
        :param order_by:  The field by which this report should be ordered.  (Currently ignored by get_row_sql)
        :return:  A list of all results (from fetchall)
        """
        sql = self.get_row_sql(filters, order_by)
        if not sql:
            return []
        cursor = self.get_cursor()
        cursor.execute(sql)
        return cursor.fetchall()
    
    def get_aggregate_data(self, filters):
        """
        Returns the cursor based on a filter dictionary.

        :param filters: A dictionary of paramters by which this report will be filtered.
        :return:  The aggregates for this report, based on the aggregate sql.
        """
        sql = self.get_aggregate_sql(filters)
        if not sql:
            return []
        cursor = self.get_cursor()
        cursor.execute(sql)
        result = cursor.fetchone()
        
        agg = list()
        for i in range(len(result)):
            agg.append((cursor.description[i][0],result[i]))
        return agg
    
    def get_filter_form(self, data):
        """
        Returns the filter form based on filter data.

        :param data: A dictionary with filters that should be used.
        :return: A filtering form for this report.
        """
        form=forms.Form(data=data)
        for q in self.query_params:
            control = FilterControl.create_from_datatype(q[2],q[0],q[1])
            fields = control.get_fields()
            form.fields.update(fields)
        form.full_clean()
        return form

    # CONSIDER not ideal in terms paging, would be better to fetch within a range..
    # TODO Make this work with order_by
    # TODO Use a generator instead of getting a big list of results.
    # TODO Make the return from this function match the implied contract from all of the other subclasses of Report.
    def get_rows(self,filters={},order_by=None):
        """
        This returns all of the rows in the report, ignores order_by

        :param filters: A dictionary of filters upon which to filter the report.
        :param order_by: The field by which the report should be ordered.
        :return:  A tuple of rows and aggregate data (no meta data!)
        """
        rows = self.get_row_data(filters, order_by)
        agg = self.get_aggregate_data(filters)
        return rows,agg

class DateSQLReport(SQLReport):
    """
    A date based SQL report.  Implies that the row and aggregate SQL should contain date__gte and date__lt variables.
    """
    aggregate_sql=None
    query_params=[("date","Date","datetime")]
    date_field="date"
    default_mask={
        "date__gte":lambda: (datetime.datetime.today() -datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
        "date__lt":lambda: (datetime.datetime.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
    }

# TODO build AnnotatedReport that deals with .annotate functions in ORM

