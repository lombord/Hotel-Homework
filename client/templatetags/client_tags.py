from django import template

register = template.Library()


@register.filter
def obj_url(obj, url_name=None):
    if url_name is None:
        return obj.get_absolute_url()
    return obj.get_absolute_url(url_name)
