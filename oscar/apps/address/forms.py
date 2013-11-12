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

    class Meta:
        model = UserAddress
        exclude = ('user', 'num_orders', 'hash', 'search_text')

    #def __init__(self, user, *args, **kwargs):
    #    super(UserAddressForm, self).__init__(*args, **kwargs)


    #    #if not self.instance.country:
    #    #    self.instance.country = Country("US")

    def __init__(self, user, *args, **kwargs):
        super(UserAddressForm, self).__init__(*args, **kwargs)
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




