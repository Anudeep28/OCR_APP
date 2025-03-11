from django import template
import json
import pprint

register = template.Library()

@register.filter
def is_list(value):
    """Check if a value is a list"""
    return isinstance(value, list)

@register.filter
def is_dict(value):
    """Check if a value is a dictionary"""
    return isinstance(value, dict)

@register.filter
def pprint(value):
    """Pretty print a value"""
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    return value

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using the key"""
    if dictionary is None:
        return ""
    return dictionary.get(key, "")

@register.filter
def replace_underscore(value):
    """Replace underscores with spaces and capitalize each word"""
    if value is None:
        return ""
    return value.replace('_', ' ').title()

@register.filter
def get_attribute(obj, attr):
    """Get an attribute from an object by name"""
    if obj is None:
        return ""
    try:
        return getattr(obj, attr, "")
    except:
        return ""

@register.filter
def split(value, delimiter):
    """Split a string into a list"""
    if value is None:
        return []
    return value.split(delimiter)
