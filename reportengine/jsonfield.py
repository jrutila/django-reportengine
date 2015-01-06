"""
Django JSON Field.  This extends Django Model Fields to store JSON as a field-type.
"""
#TODO - Move this to utils or another application.  This is tangential to reporting and useful for other things.

from django.db import models
try:
    import json as simplejson
except ImportError:
    from django.utils import simplejson
from django.core.serializers.json import DjangoJSONEncoder

import logging

class JSONFieldDescriptor(object):
    def __init__(self, field, datatype=dict):
        """
        Create a JSONFieldDescriptor

        :param field:   The field to create the descriptor for.
        :param datatype:  The datatype of the descriptor.
        """
        self.field = field
        self.datatype = datatype

    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances."
                % (self.field.name, owner.__name__))
        
        if not hasattr(instance, self.field.get_cache_name()):
            data = instance.__dict__.get(self.field.attname, self.datatype())
            if not isinstance(data, self.datatype):
                data = self.field.loads(data)
                if data is None:
                    data = self.datatype()
            setattr(instance, self.field.get_cache_name(), data)
        
        return getattr(instance, self.field.get_cache_name())

    def __set__(self, instance, value):
        if not isinstance(value, (self.datatype, basestring)):
            value = self.datatype(value)
        instance.__dict__[self.field.attname] = value
        try:
            delattr(instance, self.field.get_cache_name())
        except AttributeError:
            pass


class JSONField(models.TextField):
    """
    A field for storing JSON-encoded data. The data is accessible as standard
    Python data types and is transparently encoded/decoded to/from a JSON
    string in the database.
    """
    serialize_to_string = True
    descriptor_class = JSONFieldDescriptor

    def __init__(self, verbose_name=None, name=None,
                 encoder=DjangoJSONEncoder(), decoder=simplejson.JSONDecoder(),
                 datatype=dict,
                 **kwargs):
        """
        Create a new JSONField

        :param verbose_name:   The verbose name of the field
        :param name:    The short name of the field.
        :param encoder:   The encoder used to turn native datatypes into JSON.
        :param decoder:   The decoder used to turn JSON into native datatypes.
        :param datatype:  The native datatype to store.
        :param kwargs:    Other arguments to pass to parent constructor.
        """
        blank = kwargs.pop('blank', True)
        models.TextField.__init__(self, verbose_name, name, blank=blank,
                                  **kwargs)
        self.encoder = encoder
        self.decoder = decoder
        self.datatype = datatype

    #TODO - Is this used anywhere?  If not, let's remove it.
    def db_type(self, connection=None):
        """
        Returns the database type.  Overrides django.db.models.Field's db_type.

        :param connection:  The database connection - defaults to none.
        :return:  The database type.  Always returns the string 'text'.
        """
        return "text"


    def contribute_to_class(self, cls, name):
        """
        Overrides django.db.models.Field's contribute to class to handle descriptors.

        :param cls:  The class to contribute to.
        :param name: The name.
        """
        super(JSONField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, self.descriptor_class(self, self.datatype))
    
    def pre_save(self, model_instance, add):
        "Returns field's value just before saving.  If a descriptor, get's that instead of value from object."
        descriptor = getattr(model_instance, self.attname)
        if isinstance(descriptor, self.datatype):
            return descriptor
        return self.field.value_from_object(model_instance)

    def get_db_prep_save(self, value, *args, **kwargs):
        if not isinstance(value, basestring):
            value = self.dumps(value)

        return super(JSONField, self).get_db_prep_save(value, *args, **kwargs)

    def value_to_string(self, obj):
        """
        Turns the value to a JSON string.
        :param obj: An object.
        :return:  A string.
        """
        return self.dumps(self.value_from_object(obj))

    def dumps(self, data):
        """
        Encodes data and dumps.
        :param data: A value.
        :return:  An encoded string.
        """
        return self.encoder.encode(data)

    def loads(self, val):
        """

        :param val:  A JSON encoddd string.
        :return: A dict with data from val
        """
        try:
            val = self.decoder.decode(val)#, encoding=settings.DEFAULT_CHARSET)

            # XXX We need to investigate why this is happening once we have
            # a solid repro case.
            if isinstance(val, basestring):
                logging.warning("JSONField decode error. Expected dictionary, "
                                "got string for input '%s'" % val)
                # For whatever reason, we may have gotten back
                val = self.decoder.decode(val)#, encoding=settings.DEFAULT_CHARSET)
        except ValueError:
            val = None
        return val
    
    def south_field_triple(self):
        """
        Returns a suitable description of this field for South."

        :return: A tuple of field_class, args and kwargs from South's introspector.
        """
        # We'll just introspect the _actual_ field.
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.TextField"
        args, kwargs = introspector(self)
        # That's our definition!
        return (field_class, args, kwargs)

