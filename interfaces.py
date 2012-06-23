"""
This library is a trivial implementation of an interface in Python.
It exclusively uses decorators, does not require inheritance, and
is fairly flexible in its usage.

A simple example:

    @interfaces.define
    class BehaviorInterface(object):

        @interfaces.require
        def execute(self):
            '''All SimpleInterfaces must implement an 'execute' method.'''
            pass

    @interfaces.implement(SimpleInterface)
    class NewBehavior(object):

        @interfaces.final
        def execute(self):
            return "new behavior value"

"""

import functools

REQUIRED_ATTR = "_interfaces_required"
FINAL_ATTR = "_interfaces_final"

def define(cls):
    """Class decorator that defines an interface class."""
    cls._interfaces_required = []
    for attribute_key in dir(cls):
        attribute = getattr(cls, attribute_key)
        if getattr(attribute, REQUIRED_ATTR, False):
            cls._interfaces_required.append(attribute.__name__)
    return cls

def implement(*interfaces):
    """Class decorator that checks a class for implementation."""
    def wrapper(cls):
        for interface in interfaces:
            _check_required(interface, cls)
            _check_final(interface, cls)
        return cls
    return wrapper

def strict(cls):
    """Class decorator to run final check, etc. for non-implement classes."""
    _check_final(None, cls)
    return cls

def require(method):
    """Method decorator to indicate an interface has a required attribute."""
    doc = method.__doc__
    @functools.wraps(method)
    def capture_method(instance, *args, **kwargs):
        raise MissingRequiredAttribute(doc)
    setattr(capture_method, REQUIRED_ATTR, True)
    return capture_method

def final(method):
    """Method decorator to indicate a method is final."""
    setattr(method, FINAL_ATTR, True)
    return method

def _check_required(interface, cls):
    """Checks all required attributes on the new class."""
    for attribute_key in interface._interfaces_required:
        attribute = getattr(interface, attribute_key)
        cls_attribute = getattr(cls, attribute_key, None) or attribute

        implemented = cls_attribute and \
            not getattr(cls_attribute, REQUIRED_ATTR, False)
        if not implemented:
            docstring = attribute.__doc__
            raise MissingRequiredAttribute(docstring)

def _check_final(interface, cls):
    """Checks all attributes on the new class to ensure not final."""

    # this methodology feels hacky to me, especially with the
    # __dict__ lookups -- I think there must be a cleaner way
    # to do this.

    lookup_classes = [c for c in cls.mro()]
    lookup_classes.reverse()

    # If an interface is not in the base class list, and the
    # current class overwrites something labeled as "final" in
    # the interface, what is the expected behavior?
    #
    # Here, we fail if we write over a 'final' method in the
    # interface, even if it is not one of the base classes.
    # It complicates a simple case where you define an interface
    # with a final, implement that interface without subclassing,
    # and now you cannot call or define that final method...
    # but that's sort of stupid design anyway.

    if interface and interface not in lookup_classes:
        lookup_classes.insert(0, interface)

    for attribute_key in dir(cls):
        new_attribute = getattr(cls, attribute_key)
        # only works on methods right now...
        if not callable(new_attribute):
            continue
        is_finaled = False
        for base in lookup_classes:
            attribute = base.__dict__.get(attribute_key, None)
            if not attribute:
                continue
            if not is_finaled:
                is_finaled = getattr(attribute, FINAL_ATTR, False)
            else:
                # something flagged as final has been overwritten later
                # down the line.
                raise CannotOverrideFinal(
                    "Method %s is final -- cannot override in %s" % (
                        attribute_key, base))

class MissingRequiredAttribute(Exception):
    """Raised when a required interface method is called."""
    pass

class CannotOverrideFinal(Exception):
    """Raised when an implementation of an interface overrides a final."""
    pass