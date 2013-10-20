from django import template

register = template.Library()


@register.filter(name='cut')
def cut(value, arg):
    return value.replace(arg, '')

@register.filter(name='replace')
def replace(value, commaSepArgs):
	argList = commaSepArgs.split(',')
	s1 = argList[0]
	s2 = argList[1]
   	return value.replace(s1, s2)
