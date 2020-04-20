"""Utility methods for Cloud Storage."""
import functools

_SENTINEL = object()


def rgetattr(obj, attr, default=_SENTINEL):
    """Get a nested named attribute from an object.

    Example: ::

        b = type('B', (), {'c': True})()
        a = type('A', (), {'b': b})()
        # True

    Source:
    `getattr-and-setattr-on-nested-objects <https://stackoverflow.com/questions/
    31174295/getattr-and-setattr-on-nested-objects/31174427>`__

    :param obj: Object.
    :type obj: object

    :param attr: Dot notation attribute name.
    :type attr: str

    :param default: (optional) Sentinel value, defaults to :class:`object()`.
    :type default: object

    :return: Attribute value.
    :rtype:  object
    """
    if default is _SENTINEL:
        _getattr = getattr
    else:

        def _getattr(obj_, name):
            return getattr(obj_, name, default)

    return functools.reduce(_getattr, [obj] + attr.split("."))


def rsetattr(obj, attr, val):
    """Sets the nested named attribute on the given object to the specified
    value.

    Example: ::

        b = type('B', (), {'c': True})()
        a = type('A', (), {'b': b})()
        rsetattr(a, 'b.c', False)
        # False

    Source: `getattr-and-setattr-on-nested-objects <https://stackoverflow.com/
    questions/31174295/getattr-and-setattr-on-nested-objects/31174427>`__

    :param obj: Object.
    :type obj: object

    :param attr: Dot notation attribute name.
    :type attr: str

    :param val: Value to set.
    :type val: object

    :return: NoneType
    :rtype: None
    """
    pre, _, post = attr.rpartition(".")
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)
