from django.conf import settings
from django import forms
from django.db.models import get_model

UserAddress = get_model('address', 'useraddress')
Country = get_model('address', 'Country')


class AbstractAddressForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        """
        Set fields in OSCAR_REQUIRED_ADDRESS_FIELDS as required.
        """
        super(AbstractAddressForm, self).__init__(*args, **kwargs)
        field_names = (set(self.fields) &
                       set(settings.OSCAR_REQUIRED_ADDRESS_FIELDS))
        for field_name in field_names:
            self.fields[field_name].required = True
        print("required fields??")
        print(settings.OSCAR_REQUIRED_ADDRESS_FIELDS)    


class UserAddressForm(AbstractAddressForm):


    no_checkboxes = None

    class Meta:
        model = UserAddress
        exclude = ('user', 'num_orders', 'hash', 'search_text', 'latitude', 'longitude')

    # def __init__(self, user, *args, **kwargs):
    #     import ipdb;ipdb.set_trace()

    #     super(UserAddressForm, self).__init__(*args, **kwargs)


    #    #if not self.instance.country:
    #    #    self.instance.country = Country("US")

    def __init__(self, user, no_checkboxes=False, *args, **kwargs):

        super(UserAddressForm, self).__init__(*args, **kwargs)

        ## only show choice for default store address if a seller
        if not hasattr(user, 'partner'):
            self.fields.pop('is_default_for_store')

        if no_checkboxes == True:
            self.fields.pop('is_default_for_store')
            self.fields.pop('is_default_for_shipping')
            self.fields.pop('is_default_for_billing')                        

        self.instance.user = user
        countries = Country._default_manager.filter(
            is_shipping_country=True)

        # No need to show country dropdown if there is only one option
        if len(countries) == 1:
            del self.fields['country']
            self.instance.country = countries[0]
        else:
            self.fields['country'].queryset = countries
            self.fields['country'].empty_label = None



