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
