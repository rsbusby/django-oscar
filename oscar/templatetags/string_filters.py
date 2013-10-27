from django import template
from django.template.defaultfilters import stringfilter
import re

register = template.Library()


@register.filter
def split(value, separator=' '):
    return value.split(separator)

@register.filter()
@stringfilter
def inner_html(value):
    """ Strip off the outer tag of the HTML passed in.
    """
    if value.startswith('<'):
        value = value.split('>', 1)[1].rsplit('<', 1)[0]
    return value

@register.filter()
@stringfilter
def first_par(value):
    """ Take just the first paragraph of the HTML passed in.
    """
    return value.split("</p>")[0] + "</p>"

@register.filter
@stringfilter
def first_sentence(value):
    """ Take just the first sentence of the HTML passed in.
    """
    #value = inner_html(first_par(value))
    words = value.split()
    # Collect words until the result is a sentence.
    sentence = ""
    while words:
        if sentence:
            sentence += " "
        sentence += words.pop(0)
        if not re.search(r'[.?!][)"]*$', sentence):
            # End of sentence doesn't end with punctuation.
            continue
        if words and not re.search(r'^[("]*[A-Z0-9]', words[0]):
            # Next sentence has to start with upper case.
            continue
        if re.search(r'(Mr\.|Mrs\.|Ms\.|Dr\.| [A-Z]\.)$', sentence):
            # If the "sentence" ends with a title or initial, then it probably
            # isn't the end of the sentence.
            continue
        if sentence.count('(') != sentence.count(')'):
            # A sentence has to have balanced parens.
            continue
        if sentence.count('"') % 2:
            # A sentence has to have an even number of quotes.
            continue
        break
     
    return sentence


@register.filter
@stringfilter
def two_sentences(value):

	s1 = first_sentence(value)
	s2 = first_sentence(value[len(s1):])
	return s1 + "  " + s2
