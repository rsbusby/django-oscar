from django import forms
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django.db.models import get_model
from django.utils.translation import ugettext_lazy as _
from treebeard.forms import MoveNodeForm, movenodeform_factory

from oscar.core.utils import slugify
from oscar.forms.widgets import ImageInput

Product = get_model('catalogue', 'Product')
Category = get_model('catalogue', 'Category')
StockRecord = get_model('partner', 'StockRecord')
Partner = get_model('partner', 'Partner')
ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')
ProductCategory = get_model('catalogue', 'ProductCategory')
ProductImage = get_model('catalogue', 'ProductImage')
ProductRecommendation = get_model('catalogue', 'ProductRecommendation')

from oscar.apps.shipping.models import ShippingMethod



class BaseCategoryForm(MoveNodeForm):

    def clean(self):
        cleaned_data = super(BaseCategoryForm, self).clean()

        name = cleaned_data.get('name')
        ref_node_pk = cleaned_data.get('_ref_node_id')
        pos = cleaned_data.get('_position')

        if name and self.is_slug_conflicting(name, ref_node_pk, pos):
            raise forms.ValidationError(
                _('Category with the given path already exists.'))
        return cleaned_data

    def is_slug_conflicting(self, name, ref_node_pk, position):
        # determine parent
        if ref_node_pk:
            ref_category = Category.objects.get(pk=ref_node_pk)
            if position == 'first-child':
                parent = ref_category
            else:
                parent = ref_category.get_parent()
        else:
            parent = None

        # build full slug
        slug_prefix = (parent.slug + Category._slug_separator) if parent else ''
        slug = '%s%s' % (slug_prefix, slugify(name))

        # check if slug is conflicting
        try:
            category = Category.objects.get(slug=slug)
        except Category.DoesNotExist:
            pass
        else:
            if category.pk != self.instance.pk:
                return True
        return False

CategoryForm = movenodeform_factory(Category, form=BaseCategoryForm)


class ProductSearchForm(forms.Form):
    upc = forms.CharField(max_length=16, required=False, label=_('UPC'))
    title = forms.CharField(max_length=255, required=False, label=_('Title'))



from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Button, Row, Field
from crispy_forms.bootstrap import AppendedText, PrependedText, FormActions

SHIPPING_CHOICES = (
    ('Priority','USPS Priority Mail'),
    ('First','USPS First Class Mail'),
    ('ParcelSelect','USPS Parcel Select Mail'),
    ('UPS','UPS'),
    ('Local','Local'),
    ('SelfDelivery','Self Delivery'),
)


class StockRecordForm(forms.ModelForm):

    # radio_buttons = forms.ChoiceField(
    #     choices = (
    #         ('option_one', "Option one is this and that be sure to include why it's great"), 
    #         ('option_two', "Option two can is something else and selecting it will deselect option one")
    #     ),
    #     widget = forms.RadioSelect,
    #     initial = 'option_two',
    # )


    ##shipping_method_choices = forms.MultipleChoiceField(label="Shipping/Delivery choices", widget=forms.CheckboxSelectMultiple, choices=SHIPPING_CHOICES)


    ##shipping_methods = forms.ModelMultipleChoiceField(queryset=ShippingMethod.objects.all(),
    ##                                                widget=forms.CheckboxSelectMultiple())

    checkboxes = forms.MultipleChoiceField(
        choices = (
            ('option_one', ""), 
            ('option_two', 'Option two can also be checked and included in form results'),
            ('option_three', 'Option three can yes, you guessed it also be checked and included in form results')
        ),
        initial = 'option_one',
        required=False,
        widget = forms.CheckboxSelectMultiple,
        help_text = "<strong>Note:</strong> Labels surround all the options for much larger click areas and a more usable form.",
    )
 
    PMSmall_num = forms.IntegerField(required=False)
    PMMedium_num = forms.IntegerField(required=False)
    PMLarge_num = forms.IntegerField(required=False)

    self_ship_cost = forms.FloatField(required=False)    

    def __init__(self, product_class, *args, **kwargs):
        self.product_class = product_class
        super(StockRecordForm, self).__init__(*args, **kwargs)

        if 'price_excl_tax' in self.fields:
            self.fields['price_excl_tax'].label = "Price"
        if 'num_in_stock' in self.fields:
            self.fields['num_in_stock'].label = "Number in inventory (leave blank if this item is made to order)"

        # If not tracking stock, we hide the fields
        if not self.product_class.track_stock:
            del self.fields['num_in_stock']
            del self.fields['low_stock_threshold']

    class Meta:
        model = StockRecord
        exclude = ('product', 'num_allocated', 'price_currency', 'low_stock_threshold','price_retail', 'cost_price', 
            'partner', 'partner_sku','latitude', 'longitude')
        # widgets = {
        #     'shipping_methods': forms.CheckboxSelectMultiple()
        # }


    #def save(self):
    #    super(StockRecordForm, self).save(commit=commit)

    def is_valid(self):

        is_valid = super(StockRecordForm, self).is_valid()

        ## process shipping options
        soptsDict = {}
        data = self.data

        ## add shipping options to the stockrecord
        shipChoice = data.get('shipChoice')
        soptsDict['shipChoice'] = data.get("shipChoice")

        if shipChoice == "calculate_ship":
            soptsDict['calculate_ship'] = True
            soptsDict['self_ship'] = False
            if data.get('print_label_toggle') == "on":
                soptsDict['printLabel'] = True

        ## priority mail
        soptsDict['PMMedium_num'] = data.get("PMMedium_num")
        soptsDict['PMLarge_num'] = data.get("PMLarge_num")
        soptsDict['PMSmall_num'] = data.get("PMSmall_num")
    
        if data.get("PMSmall_toggle") == "on" and data.get('PM_toggle') == "on":
            soptsDict['PMSmall_used'] = True           
            if soptsDict.get("PMSmall_num"):
                self.instance.is_shippable = True  
            elif shipChoice == "calculate_ship":             
                is_valid = False     

        if data.get("PMMedium_toggle") == "on" and data.get('PM_toggle') == "on":
            soptsDict['PMMedium_used'] = True           
            if soptsDict.get("PMMedium_num"):
                self.instance.is_shippable = True  
            elif shipChoice == "calculate_ship":             
                is_valid = False     

        if data.get("PMLarge_toggle") == "on" and data.get('PM_toggle') == "on":
            soptsDict['PMLarge_used'] = True           
            if soptsDict.get("PMLarge_num"):
                self.instance.is_shippable = True  
            elif shipChoice == "calculate_ship":             
                is_valid = False     

        if data.get("FirstClass_toggle") == "on":
            soptsDict['first_used'] = True  
            soptsDict['parcel_select_used'] = True  
        else:
            soptsDict['first_used'] = False
            soptsDict['parcel_select_used'] = False 

        if data.get("UPS_toggle") == "on":
            soptsDict['UPS_used'] = True  
        else:
            soptsDict['UPS_used'] = False 

        if data.get("max_per_box"):
            soptsDict['max_per_box'] = data.get("max_per_box")

        if data.get("local_delivery_toggle") == "on":
            soptsDict['local_delivery_used'] = True 
        else:
            soptsDict['local_delivery_used'] = False 


        if data.has_key("self_ship_cost"):

            self_ship_cost = data['self_ship_cost']

            ## add shipping options to the stockrecord
            if self_ship_cost != '' and self_ship_cost != None:
                soptsDict['self_ship_cost'] = self_ship_cost
                if shipChoice == "self_ship":
                    self.instance.is_shippable = True


        if shipChoice == "self_ship" and data.get('remote_ship_toggle') == "on":
            soptsDict['calculate_ship'] = False
            soptsDict['self_ship'] = True 
            if not soptsDict.get('self_ship_cost'):
                is_valid = False




        import json
        self.instance.shipping_options = json.dumps(soptsDict)

        if (soptsDict.get('first_used') or soptsDict.get('parcel_select_used') or soptsDict.get('UPS_used') ) and self.cleaned_data.get('weight') > 0.0:
            self.instance.is_shippable = True

        if data.get('remote_ship_toggle') != "on":
            soptsDict['calculate_ship'] = False
            soptsDict['self_ship'] = False
            self.instance.is_shippable = False

        #self.instance.save()

        return is_valid

    def clean_weight(self):

        data = self.data
        if data.get('shipChoice') == 'calculate_ship' and data.get('remote_ship_toggle') == "on" and (data.get('UPS_toggle') == "on" or data.get('FirstClass_toggle') == "on") and not self.cleaned_data['weight']:
            raise forms.ValidationError(_("If item is to be shipped by UPS or First Class mail, please give an estimated weight for the item."))

        return self.cleaned_data['weight']

    def clean_local_pickup_enabled(self):

        data = self.data
        if not data.get('shipChoice') and not data.get('local_pickup_enabled') and not data.get('local_delivery_toggle') == 'on':
            raise forms.ValidationError(_("You have not selected any delivery method. Please select a method of shipping and/or local pickup or delivery."))

        return self.cleaned_data.get('local_pickup_enabled')

    def clean_is_shippable(self):

        data = self.data
        return self.cleaned_data['is_shippable']

        ## no validation if not shipping
        if data.get('remote_ship_toggle') != "on":
            return self.cleaned_data['is_shippable']

        if data.get('shipChoice') == 'self_ship':
            if not data.get('self_ship_cost'):
                raise forms.ValidationError(_("Please enter the cost of shipping."))

        if data.get('shipChoice') == 'calculate_ship':
            if data.get('PMSmall_toggle') == "on" and not data.get('PMSmall_num'):
                raise forms.ValidationError(_("Please enter the number of items per box."))

        if data.get('shipChoice') == 'calculate_ship':
            if data.get('PMMedium_toggle') == "on" and not data.get('PMMedium_num'):
                raise forms.ValidationError(_("Please enter the number of items per box."))

        if data.get('shipChoice') == 'calculate_ship':
            if data.get('PMLarge_toggle') == "on" and not data.get('PMLarge_num'):
                raise forms.ValidationError(_("Please enter the number of items per box."))

        return self.cleaned_data['is_shippable']


    def clean_PMSmall_num(self):

        data = self.data
        if data.get('shipChoice') == 'calculate_ship' and data.get('PM_toggle') == "on" and data.get('remote_ship_toggle') == "on":
            if data.get('PMSmall_toggle') == "on" and not data.get('PMSmall_num'):
                raise forms.ValidationError(_("Please enter the number of items per box."))
        return data.get('PMSmall_num')

    def clean_PMMedium_num(self):
        data = self.data

        if data.get('shipChoice') == 'calculate_ship' and data.get('PM_toggle') == "on" and data.get('remote_ship_toggle') == "on":
            if data.get('PMMedium_toggle') == "on" and not data.get('PMMedium_num'):
                raise forms.ValidationError(_("Please enter the number of items per box."))
        return data.get('PMMedium_num')

    def clean_PMLarge_num(self):
        data = self.data

        if data.get('shipChoice') == 'calculate_ship' and data.get('PM_toggle') == "on" and data.get('remote_ship_toggle') == "on":
            if data.get('PMLarge_toggle') == "on" and not data.get('PMLarge_num'):
                raise forms.ValidationError(_("Please enter the number of items per box."))
        return data.get('PMLarge_num')

    def clean_self_ship_cost(self):
        data = self.data
        if data.get('remote_ship_toggle') == "on":
            if data.get('shipChoice') == 'self_ship':
                if self.cleaned_data.get('self_ship_cost') == None or self.cleaned_data.get('self_ship_cost') == '':
                    raise forms.ValidationError(_("Please enter the cost of shipping."))
        return self.cleaned_data.get('self_ship_cost')

def _attr_text_field(attribute):
    return forms.CharField(label=attribute.name,
                           required=attribute.required)


def _attr_textarea_field(attribute):
    return forms.CharField(label=attribute.name,
                           widget=forms.Textarea(),
                           required=attribute.required)


def _attr_integer_field(attribute):
    return forms.IntegerField(label=attribute.name,
                              required=attribute.required)


def _attr_boolean_field(attribute):
    return forms.BooleanField(label=attribute.name,
                              required=attribute.required)


def _attr_float_field(attribute):
    return forms.FloatField(label=attribute.name,
                            required=attribute.required)


def _attr_date_field(attribute):
    return forms.DateField(label=attribute.name,
                           required=attribute.required,
                           widget=forms.widgets.DateInput)


def _attr_option_field(attribute):
    return forms.ModelChoiceField(
        label=attribute.name,
        required=attribute.required,
        queryset=attribute.option_group.options.all())


def _attr_multi_option_field(attribute):
    return forms.ModelMultipleChoiceField(
        label=attribute.name,
        required=attribute.required,
        queryset=attribute.option_group.options.all())


def _attr_entity_field(attribute):
    return forms.ModelChoiceField(
        label=attribute.name,
        required=attribute.required,
        queryset=attribute.entity_type.entities.all())


def _attr_numeric_field(attribute):
    return forms.FloatField(label=attribute.name,
                            required=attribute.required)


class ProductForm(forms.ModelForm):

    FIELD_FACTORIES = {
        "text": _attr_text_field,
        "richtext": _attr_textarea_field,
        "integer": _attr_integer_field,
        "boolean": _attr_boolean_field,
        "float": _attr_float_field,
        "date": _attr_date_field,
        "option": _attr_option_field,
        "multi_option": _attr_multi_option_field,
        "entity": _attr_entity_field,
        "numeric": _attr_numeric_field,
    }

    def __init__(self, product_class, *args, **kwargs):
        self.product_class = product_class
        self.set_initial_attribute_values(kwargs)
        super(ProductForm, self).__init__(*args, **kwargs)
        self.add_attribute_fields()
        related_products = self.fields.get('related_products', None)
        if 'title' in self.fields:
            self.fields['title'].label = "Item name"
        if 'description' in self.fields:
            self.fields['description'].label = "Item description"
            self.fields['description'].widget.attrs['rows'] = 2

        if 'related_products' in self.fields:
            self.fields['related_products'].label = "Related items"
        if 'parent' in self.fields and self.instance.pk is not None:
            # Prevent selecting itself as parent
            parent = self.fields['parent']
            parent.queryset = parent.queryset.exclude(
                pk=self.instance.pk).filter(parent=None)
        if related_products is not None:
            related_products.queryset = self.get_related_products_queryset()
        if 'title' in self.fields:
            self.fields['title'].widget = forms.TextInput(
                attrs={'autocomplete': 'off'})

    def set_initial_attribute_values(self, kwargs):
        if kwargs.get('instance', None) is None:
            return
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        for attribute in self.product_class.attributes.all():
            try:
                value = kwargs['instance'].attribute_values.get(
                    attribute=attribute).value
            except ProductAttributeValue.DoesNotExist:
                pass
            else:
                kwargs['initial']['attr_%s' % attribute.code] = value

    def add_attribute_fields(self):
        for attribute in self.product_class.attributes.all():
            self.fields['attr_%s' % attribute.code] = \
                    self.get_attribute_field(attribute)

    def get_attribute_field(self, attribute):
        return self.FIELD_FACTORIES[attribute.type](attribute)

    def get_related_products_queryset(self):
        return Product.browsable.order_by('title')

    class Meta:
        model = Product
        exclude = ('slug', 'status', 'score', 'product_class',
                   'recommended_products', 'product_options',
                   'attributes', 'categories', 'parent', 'upc', 'is_discountable', 'related_products')

    def save(self):
        object = super(ProductForm, self).save(False)
        object.product_class = self.product_class

        for attribute in self.product_class.attributes.all():
            value = self.cleaned_data['attr_%s' % attribute.code]
            setattr(object.attr, attribute.code, value)
        if not object.upc:
            object.upc = None
        object.save()
        if hasattr(self, 'save_m2m'):
            self.save_m2m()
        return object

    def save_attributes(self, object):
        for attribute in self.product_class.attributes.all():
            value = self.cleaned_data['attr_%s' % attribute.code]
            attribute.save_value(object, value)

    def clean(self):
        data = self.cleaned_data
        if 'parent' not in data and not data['title']:
            raise forms.ValidationError(_("This field is required"))
        elif 'parent' in data and data['parent'] is None and not data['title']:
            raise forms.ValidationError(_("Parent products must have a title"))
        # Calling the clean() method of BaseForm here is required to apply
        # checks for 'unique' field. This prevents e.g. the UPC field from
        # raising a DatabaseError.
        return super(ProductForm, self).clean()


class StockAlertSearchForm(forms.Form):
    status = forms.CharField(label=_('Status'))


class ProductCategoryForm(forms.ModelForm):

    class Meta:
        model = ProductCategory


class BaseProductCategoryFormSet(BaseInlineFormSet):

    # def __init__(self, *args, **kwargs):
    #     self.extra = 2
    #     self.max_num = 2 #4
    #     super(BaseInlineFormSet, self).__init__(*args, **kwargs)


    def clean(self):
        # if self.instance.is_top_level and self.get_num_categories() == 0:
        #     raise forms.ValidationError(
        #         _("Please add a category for this item. Choose 'Other' if there is not a more appropriate category."))
        if self.instance.is_variant and self.get_num_categories() > 0:
            raise forms.ValidationError(
                _("A variant product should not have categories"))

    def get_num_categories(self):
        num_categories = 0
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            if (hasattr(form, 'cleaned_data')
                    and form.cleaned_data.get('category', None)
                    and form.cleaned_data.get('DELETE', False) != True):
                num_categories += 1
        return num_categories


ProductCategoryFormSet = inlineformset_factory(
    Product, ProductCategory, form=ProductCategoryForm,
    formset=BaseProductCategoryFormSet, fields=('category',), extra=1,
    can_delete=False)





class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        exclude = ('display_order',)
        # use ImageInput widget to create HTML displaying the
        # actual uploaded image and providing the upload dialog
        # when clicking on the actual image.
        widgets = {
            'original': ImageInput(),
        }



    def save(self, *args, **kwargs):
        # We infer the display order of the image based on the order of the
        # image fields within the formset.
        kwargs['commit'] = False
        obj = super(ProductImageForm, self).save(*args, **kwargs)
        obj.display_order = self.get_display_order()
        obj.save()
        return obj

    def get_display_order(self):
        return self.prefix.split('-').pop()

## this was the original, not using minimum formset
ProductImageFormSet = inlineformset_factory(
     Product, ProductImage, form=ProductImageForm, extra=2)

## the following class lets you require a miniumum of one image. 
class MinimumRequiredFormSet(forms.models.BaseInlineFormSet):
    """
    Inline formset that enforces a minimum number of non-deleted forms
    that are not empty
    """
    default_minimum_forms_message = "At least %s set%s of data is required"


    def __init__(self, *args, **kwargs):
        self.minimum_forms = kwargs.pop('minimum_forms', 0)
        ## show one extra place to upload images
        self.extra = 2
        self.max_num = 3 #4
        minimum_forms_message = kwargs.pop('minimum_forms_message', None)
        if minimum_forms_message:
            self.minimum_forms_message = minimum_forms_message
        else:
            self.minimum_forms_message = \
                self.default_minimum_forms_message % (
                    self.minimum_forms,
                    '' if self.minimum_forms == 1 else 's'
                )

        super(MinimumRequiredFormSet, self).__init__(*args, **kwargs)

    def clean(self):
        non_deleted_forms = self.total_form_count()
        non_empty_forms = 0
        for i in xrange(0, self.total_form_count()):
            form = self.forms[i]
            if self.can_delete and self._should_delete_form(form):
                non_deleted_forms -= 1
            if not (form.instance.id is None and not form.has_changed()):
                non_empty_forms += 1
        if (
            non_deleted_forms < self.minimum_forms
            or non_empty_forms < self.minimum_forms
        ):
            raise forms.ValidationError(self.minimum_forms_message)




## the following formset lets you require a miniumum of one image. 

# ProductImageFormSet = inlineformset_factory(
#     Product,
#     ProductImage,
#     formset=MinimumRequiredFormSet,
#     form=ProductImageForm,
# )


ProductRecommendationFormSet = inlineformset_factory(
    Product, ProductRecommendation, extra=5, fk_name="primary")
