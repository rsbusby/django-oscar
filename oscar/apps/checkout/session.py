import logging

from django.db.models import get_model

from oscar.apps.shipping.methods import Free, LocalPickup, SelfDelivery
from oscar.core.loading import get_class
OrderTotalCalculator = get_class('checkout.calculators', 'OrderTotalCalculator')
CheckoutSessionData = get_class('checkout.utils', 'CheckoutSessionData')

ShippingAddress = get_model('order', 'ShippingAddress')
UserAddress = get_model('address', 'UserAddress')

# Standard logger for checkout events
logger = logging.getLogger('oscar.checkout')


class CheckoutSessionMixin(object):
    """
    Mixin to provide common functionality shared between checkout views.
    """

    def dispatch(self, request, *args, **kwargs):

        self.checkout_session = CheckoutSessionData(request)
        return super(CheckoutSessionMixin, self).dispatch(request, *args, **kwargs)

    def get_shipping_address(self):
        """
        Return the current shipping address for this checkout session.

        This could either be a ShippingAddress model which has been
        pre-populated (not saved), or a UserAddress model which will
        need converting into a ShippingAddress model at submission
        """
        addr_data = self.checkout_session.new_shipping_address_fields()
        if addr_data:
            # Load address data into a blank address model
            return ShippingAddress(**addr_data)
        addr_id = self.checkout_session.user_address_id()
        if addr_id:
            try:
                return UserAddress._default_manager.get(pk=addr_id)
            except UserAddress.DoesNotExist:
                # This can happen if you reset all your tables and you still
                # have session data that refers to addresses that no longer
                # exist.
                pass
        return None

    def get_shipping_method(self, basket=None):

        method = self.checkout_session.shipping_method(basket)

        # We default to nothing (or could be using free local pickup)
        if not method:
            #method = LocalPickup()
            method = None
        return method

    def get_order_totals(self, basket=None, shipping_method=None, **kwargs):
        """
        Returns the total for the order with and without tax (as a tuple)
        """
        calc = OrderTotalCalculator(self.request)
        if not basket:
            basket = self.request.basket
        if not shipping_method:
            shipping_method = self.get_shipping_method(basket)
        total_incl_tax = calc.order_total_incl_tax(basket, shipping_method, **kwargs)
        total_excl_tax = calc.order_total_excl_tax(basket, shipping_method, **kwargs)
        return total_incl_tax, total_excl_tax

    def get_order_shipping_cost(self, basket=None, shipping_method=None, **kwargs):
        """
        Returns the shipping cost
        """

        if not basket:
            basket = self.request.basket
        if not shipping_method:
            shipping_method = self.get_shipping_method(basket)
        shippingCost = shipping_method.basket_charge_excl_tax()

        ##calc = OrderTotalCalculator(self.request)
        ##shipping_excl_tax = calc.shipping_cost(basket, shipping_method, **kwargs)
        return shippingCost

    def get_context_data(self, **kwargs):
        """
        Assign common template variables to the context.
        """

        ctx = super(CheckoutSessionMixin, self).get_context_data(**kwargs)
        try:
            ctx['shipping_address'] = self.get_shipping_address()
        except:
            ctx['shipping_address'] = None

        method = self.get_shipping_method()
        if method:
            method_code = method.code
            ctx['shipping_method'] = method
            #if self.checkout_session.get_shipping_cost(method_code):
            #    ctx['shipping_total_excl_tax'] = self.checkout_session.get_shipping_cost(method_code)
            #else:
            charge = method.basket_charge_excl_tax()
            ctx['shipping_total_excl_tax'] = charge
            self.checkout_session.set_shipping_cost(method_code, charge)

            #if self.checkout_session.get_shipping_cost(method_code):
            #    ctx['shipping_total_incl_tax'] = self.checkout_session.get_shipping_cost(method_code)
            #else:
            charge = method.basket_charge_incl_tax()
            ctx['shipping_total_incl_tax'] = charge
            self.checkout_session.set_shipping_cost(method_code, charge) 

        
        cur_totals = self.checkout_session.order_totals()
        if not cur_totals[0] or cur_totals[1]:
            ti, te = self.get_order_totals()
            self.checkout_session.set_order_totals(ti, te)            
        ctx['order_total_incl_tax'], ctx['order_total_excl_tax'] = self.checkout_session.order_totals()

        ctx['payment_method'] = self.checkout_session.payment_method()

        return ctx
