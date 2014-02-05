import logging

from django.http import Http404, HttpResponseRedirect, HttpResponseBadRequest
from django.core.urlresolvers import reverse, reverse_lazy

from django.contrib import messages
from django.conf import settings

from django.contrib.auth import login
from django.db.models import get_model
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, TemplateView, FormView, \
                                 DeleteView, UpdateView, CreateView
from oscar.apps.customer.utils import normalise_email

from oscar.apps.shipping.methods import NoShippingRequired
from oscar.core.loading import get_class, get_classes

from oscar.apps.order.models import SponsoredOrganization
from oscar.apps.payment.models import SourceType, Source

from django.contrib.sites.models import Site, get_current_site
Dispatcher = get_class('customer.utils', 'Dispatcher')

from apps.homemade.homeMade import  *

ShippingAddressForm, GatewayForm = get_classes('checkout.forms', ['ShippingAddressForm', 'GatewayForm'])
OrderTotalCalculator = get_class('checkout.calculators', 'OrderTotalCalculator')
CheckoutSessionData = get_class('checkout.utils', 'CheckoutSessionData')
pre_payment, post_payment = get_classes('checkout.signals', ['pre_payment', 'post_payment'])
OrderNumberGenerator, OrderCreator = get_classes('order.utils', ['OrderNumberGenerator', 'OrderCreator'])
UserAddressForm = get_class('address.forms', 'UserAddressForm')
Repository = get_class('shipping.repository', 'Repository')
SellerCannotShip = get_class('shipping.repository', 'SellerCannotShip')
AccountAuthView = get_class('customer.views', 'AccountAuthView')
RedirectRequired, UnableToTakePayment, PaymentError = get_classes(
    'payment.exceptions', ['RedirectRequired', 'UnableToTakePayment', 'PaymentError'])
UnableToPlaceOrder = get_class('order.exceptions', 'UnableToPlaceOrder')
OrderPlacementMixin = get_class('checkout.mixins', 'OrderPlacementMixin')
CheckoutSessionMixin = get_class('checkout.session', 'CheckoutSessionMixin')

Order = get_model('order', 'Order')
ShippingAddress = get_model('order', 'ShippingAddress')
CommunicationEvent = get_model('order', 'CommunicationEvent')
PaymentEventType = get_model('order', 'PaymentEventType')
PaymentEvent = get_model('order', 'PaymentEvent')
UserAddress = get_model('address', 'UserAddress')
Basket = get_model('basket', 'Basket')
Email = get_model('customer', 'Email')
CommunicationEventType = get_model('customer', 'CommunicationEventType')

# Standard logger for checkout events
logger = logging.getLogger('oscar.checkout')


class IndexView(CheckoutSessionMixin, FormView):
    """
    First page of the checkout.  We prompt user to either sign in, or
    to proceed as a guest (where we still collect their email address).
    """
    template_name = 'checkout/gateway.html'
    form_class = GatewayForm
    success_url = reverse_lazy('checkout:shipping-address')

    def get(self, request, *args, **kwargs):
        # We redirect immediately to shipping address stage if the user is
        # signed in
        if request.user.is_authenticated():
            return self.get_success_response()
        return super(IndexView, self).get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(IndexView, self).get_form_kwargs()
        email = self.checkout_session.get_guest_email()
        if email:
            kwargs['initial'] = {
                'username': email,
            }
        return kwargs

    def form_valid(self, form):
        if form.is_guest_checkout() or form.is_new_account_checkout():
            email = form.cleaned_data['username']
            self.checkout_session.set_guest_email(email)

            if form.is_new_account_checkout():
                messages.info(
                    self.request,
                    _("Create your account and then you will be redirected "
                      "back to the checkout process"))
                self.success_url = "%s?next=%s&email=%s" % (
                    reverse('customer:register'),
                    reverse('checkout:shipping-address'),
                    email
                )
        else:
            user = form.get_user()
            login(self.request, user)

        return self.get_success_response()

    def get_success_response(self):
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return self.success_url


# ================
# SHIPPING ADDRESS
# ================


class ShippingAddressView(CheckoutSessionMixin, FormView):
    """
    Determine the shipping address for the order.

    The default behaviour is to display a list of addresses from the users's
    address book, from which the user can choose one to be their shipping address.
    They can add/edit/delete these USER addresses.  This address will be
    automatically converted into a SHIPPING address when the user checks out.

    Alternatively, the user can enter a SHIPPING address directly which will be
    saved in the session and later saved as ShippingAddress model when the order
    is sucessfully submitted.
    """
    template_name = 'checkout/shipping_address.html'
    form_class = ShippingAddressForm

    def get(self, request, *args, **kwargs):


        ## for now, disable
        seller = request.basket.seller
        if not settings.CHECKOUT_ENABLED and not seller.status == seller.APPROVED:
            messages.warning(request, _("Checkout is disabled until the site launches. We'll let you know by email when it's ready!"))
            return HttpResponseRedirect(reverse('basket:summary'))

        # Check that the user's basket is not empty
        if request.basket.is_empty:
            messages.error(request, _("You need to add some items to your basket to checkout"))
            return HttpResponseRedirect(reverse('basket:summary'))

        # Check that guests have entered an email address
        if not request.user.is_authenticated() and not self.checkout_session.get_guest_email():
            messages.error(request, _("Please either sign in or enter your email address"))
            return HttpResponseRedirect(reverse('checkout:index'))

        # Check to see that a shipping address is actually required.  It may not be if
        # the basket is purely downloads
        if not request.basket.is_shipping_required():
            messages.info(request, _("Your basket does not require a shipping address to be submitted"))
            return HttpResponseRedirect(self.get_success_url())

        return super(ShippingAddressView, self).get(request, *args, **kwargs)

    def get_initial(self):
        return self.checkout_session.new_shipping_address_fields()

    def get_context_data(self, **kwargs):
        kwargs = super(ShippingAddressView, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            # Look up address book data
            kwargs['addresses'] = self.get_available_addresses()
        return kwargs

    def get_available_addresses(self):
        return UserAddress._default_manager.filter(user=self.request.user).order_by('-is_default_for_shipping')

    def post(self, request, *args, **kwargs):
        # Check if a shipping address was selected directly (eg no form was
        # filled in)
        if self.request.user.is_authenticated() and 'address_id' in self.request.POST:
            address = UserAddress._default_manager.get(
                pk=self.request.POST['address_id'], user=self.request.user)
            action = self.request.POST.get('action', None)
            if action == 'ship_to':
                # User has selected a previous address to ship to
                self.checkout_session.ship_to_user_address(address)
                return HttpResponseRedirect(self.get_success_url())
            elif action == 'delete':
                # Delete the selected address
                address.delete()
                messages.info(self.request, _("Address deleted from your address book"))
                return HttpResponseRedirect(reverse('checkout:shipping-method'))
            else:
                return HttpResponseBadRequest()
        else:
            return super(ShippingAddressView, self).post(
                request, *args, **kwargs)

    def form_valid(self, form):
        # Store the address details in the session and redirect to next step
        address_fields = dict(
            (k, v) for (k, v) in form.instance.__dict__.items()
            if not k.startswith('_'))
        self.checkout_session.ship_to_new_address(address_fields)
        return super(ShippingAddressView, self).form_valid(form)

    def get_success_url(self):
        return reverse('checkout:shipping-method')


class UserAddressUpdateView(CheckoutSessionMixin, UpdateView):
    """
    Update a user address
    """
    template_name = 'checkout/user_address_form.html'
    form_class = UserAddressForm

    def get_queryset(self):
        return self.request.user.addresses.all()

    def get_form_kwargs(self):
        kwargs = super(UserAddressUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        messages.info(self.request, _("Address saved"))
        return reverse('checkout:shipping-address')


class UserAddressDeleteView(CheckoutSessionMixin, DeleteView):
    """
    Delete an address from a user's addressbook.
    """
    template_name = 'checkout/user_address_delete.html'

    def get_queryset(self):
        return self.request.user.addresses.all()

    def get_success_url(self):
        messages.info(self.request, _("Address deleted"))
        return reverse('checkout:shipping-address')


# ===============
# Shipping method
# ===============


class ShippingMethodView(CheckoutSessionMixin, TemplateView):
    """
    View for allowing a user to choose a shipping method.

    Shipping methods are largely domain-specific and so this view
    will commonly need to be subclassed and customised.

    The default behaviour is to load all the available shipping methods
    using the shipping Repository.  If there is only 1, then it is
    automatically selected.  Otherwise, a page is rendered where
    the user can choose the appropriate one.
    """
    template_name = 'checkout/shipping_methods.html'

    def get(self, request, *args, **kwargs):


        if request.GET.has_key('basket_id'):
            try:
                self.basket = Basket.objects.filter(id=request.GET['basket_id'])[0]
                request.basket = self.basket

                self.checkout_session = CheckoutSessionData(request)
                if self.checkout_session == {}:
                    return HttpResponseRedirect(reverse('checkout:shipping-address', basket_id=self.basket.id))

            except:
                ## ignore input, give default basket from request. Could also check that basket is for user here
                pass


        self.checkout_session.unset_shipping_method()

        # Check that the user's basket is not empty
        if request.basket.is_empty:
            messages.error(request, _("You need to add some items to your basket to checkout"))
            return HttpResponseRedirect(reverse('basket:summary'))

        # Check that shipping is required at all
        if not request.basket.is_shipping_required():
            self.checkout_session.use_shipping_method(NoShippingRequired().code)
            return self.get_success_response()

        shipping_method = self.checkout_session.shipping_method(self.request.basket)

        try:
            shipping_code = shipping_method.code
        except:
            shipping_code = None

        # Check that shipping address has been completed
        if not self.checkout_session.is_shipping_address_set() and shipping_code != "local-pickup":
            messages.info(request, _("Please choose a shipping address"))
            return HttpResponseRedirect(reverse('checkout:shipping-address'))

        # Save shipping methods as instance var as we need them both here
        # and when setting the context vars.
        self._methods = self.get_available_shipping_methods()

        #for m in self._methods:
        #    m.basket_total_shipping = None

        if len(self._methods) == 0:
            # No shipping methods available for given address
            messages.warning(request, _("Shipping is not available for your chosen address - please choose another"))
            return HttpResponseRedirect(reverse('checkout:shipping-address'))
        #elif len(self._methods) == 1:
        #    # Only one shipping method - set this and redirect onto the next step
        #    self.checkout_session.use_shipping_method(self._methods[0].code)
        #    return self.get_success_response()

        # Must be more than one available shipping method, we present them to
        # the user to make a choice.



        return super(ShippingMethodView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super(ShippingMethodView, self).get_context_data(**kwargs)
        kwargs['methods'] = self._methods
        return kwargs

    def get_available_shipping_methods(self):
        """
        Returns all applicable shipping method objects
        for a given basket.
        """
        # Shipping methods can depend on the user, the contents of the basket
        # and the shipping address.  I haven't come across a scenario that doesn't
        # fit this system.

        ## if Seller is not set up for card payments, only allow local pickup
        try:
            methods =  Repository().get_shipping_methods(self.request.user, self.request.basket,
                                                 self.get_shipping_address())
        except SellerCannotShip, e:
            print "order_kwargs"
        return methods


    def sendQueryToSeller(self, request):

        import ipdb;ipdb.set_trace()
        basket = request.basket
        seller = basket.seller

        sellerUser = seller.user

        ctx = {'user': self.request.user,
               'basket': basket,
               'site': get_current_site(self.request),
               'lines': basket.lines.all()}

        site = Site.objects.get_current()
        path = reverse('basket:single') + "?basket_id=" + str(basket.id)

        ctx['shipQuoteUrl'] = 'http://%s%s' % (site.domain, path)
        ctx['basket_total'] = basket.total_incl_tax
        shipAddressId = self.checkout_session.shipping_user_address_id()
        if shipAddressId:
            shipAddress = UserAddress.objects.get(id=shipAddressId)
        else:
            shipAddress = None
        ctx['shipping_address'] = shipAddress

        ## send the email to seller with a link to the basket ship estimate form
        messages = CommunicationEventType.objects.get_and_render('SHIP_QUOTE_SELLER', ctx)
        event_type = None

        if messages and messages['body']:
            #logger.info("Order #%s - sending %s messages", order.number, code)
            dispatcher = Dispatcher(logger)
            dispatcher.dispatch_user_messages(sellerUser, messages,
                                               event_type)

        return True

    def post(self, request, *args, **kwargs):
        # Need to check that this code is valid for this user
        if request.POST.get('method_reset'):
            self.checkout_session.unset_shipping_method()

        ## if method is get shipping estimate, then do this
        if request.POST.get('query-needed'):
            self.sendQueryToSeller(request)
            messages.success(request, _("The seller has been contacted about determining the shipping cost."))

            return HttpResponseRedirect(reverse('catalogue:index'))


        method_code = request.POST.get('method_code', None)
        is_valid = False
        newMethod = None
        methods = Repository().get_shipping_methods_no_reset(self.request.user, self.request.basket,
                                                 self.get_shipping_address())
        #for method in self.get_available_shipping_methods():

        for method in methods:
            if method.code == method_code:
                is_valid = True
                newMethod = method
        if not is_valid:
            messages.error(request, _("Your submitted shipping method is not permitted"))
            return HttpResponseRedirect(reverse('checkout:shipping-method'))



        # Save the code for the chosen shipping method in the session
        # and continue to the next step.
        order_total_incl_tax = newMethod.basket_charge_incl_tax()
        order_total_excl_tax = newMethod.basket_charge_excl_tax()

        self.checkout_session.use_shipping_method(method_code)

        return self.get_success_response()

    def get_success_response(self):
        return HttpResponseRedirect(reverse('checkout:preview'))


# ==============
# Payment method
# ==============


class PaymentMethodView(CheckoutSessionMixin, TemplateView):
    """
    View for a user to choose which payment method(s) they want to use.

    This would include setting allocations if payment is to be split
    between multiple sources.
    """

    def get(self, request, *args, **kwargs):
        # Check that the user's basket is not empty
        if request.basket.is_empty:
            messages.error(request, _("You need to add some items to your basket to checkout"))
            return HttpResponseRedirect(reverse('basket:summary'))

        shipping_required = request.basket.is_shipping_required()

        # Check that shipping address has been completed
        #if shipping_required and not self.checkout_session.is_shipping_address_set():
        #    messages.error(request, _("Please choose a shipping address"))
        #    return HttpResponseRedirect(reverse('checkout:shipping-address'))

        # Check that shipping method has been set
        #if shipping_required and not self.checkout_session.is_shipping_method_set():
        #    messages.error(request, _("Please choose a shipping method"))
        #    return HttpResponseRedirect(reverse('checkout:shipping-method'))

        return self.get_success_response()

    def get_success_response(self):
        return HttpResponseRedirect(reverse('checkout:payment-details'))


# ================
# Order submission
# ================


class PaymentDetailsView(OrderPlacementMixin, TemplateView):
    """
    For taking the details of payment and creating the order

    The class is deliberately split into fine-grained methods, responsible for
    only one thing.  This is to make it easier to subclass and override just
    one component of functionality.

    All projects will need to subclass and customise this class.
    """
    template_name = 'checkout/payment_details.html'
    template_name_preview = 'checkout/preview.html'
    preview = False
    basket = None

    def get(self, request, *args, **kwargs):


        ## for now, disable
        seller = request.basket.seller
        if not settings.CHECKOUT_ENABLED and not seller.status == seller.APPROVED:
        ##if not settings.CHECKOUT_ENABLED:
            messages.warning(request, _("Checkout is disabled until the site launches. We'll let you know by email when it's ready!"))
            return HttpResponseRedirect(reverse('basket:summary'))

        if request.GET.has_key('basket_id'):
            try:
                self.basket = Basket.objects.filter(id=request.GET['basket_id'])[0]
                request.basket = self.basket

                self.checkout_session = CheckoutSessionData(request)
                request.session['cur_basket_id'] = str(request.basket.id)
                if self.checkout_session == {}:
                    return HttpResponseRedirect(reverse('checkout:shipping-address', basket_id=self.basket.id))
            except:
                ## ignore input, give default basket from request. Could also check that basket is for user here
                pass
  

        error_response = self.get_error_response()


        if error_response:
            return error_response





        return super(PaymentDetailsView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        This method is designed to be overridden by subclasses which will
        validate the forms from the payment details page.  If the forms are
        valid then the method can call submit()
        """
       
        if request.POST.has_key('payment_method'):
            method_code = request.POST['payment_method']
            self.checkout_session.pay_by(method_code)


        if request.POST.has_key('setSponsoredOrg') or request.POST.has_key('unsetSponsoredOrg'):
            basket = Basket.objects.filter(id=request.POST['basket_id'])[0]

            if request.POST.has_key('setSponsoredOrg'):
                sOrg = SponsoredOrganization.objects.filter(id=request.POST['sponsored_org_id'])[0]
                basket.sponsored_org = sOrg
                basket.save()
            if request.POST.has_key('unsetSponsoredOrg'):   
                basket.sponsored_org = None
                basket.save()
            ## ok, now should GET this page....
            request.basket = basket
            return self.get(request, *args, **kwargs)


        if request.POST.has_key('place-order'):
            if not request.POST.has_key('basket_id'):
                return self.get(request, **kwargs)
            basket = Basket.objects.filter(id=request.POST['basket_id'])[0]

            # from apps.homemade.homeMade import chargeSharedOscar
            # order_number = self.generate_order_number(basket)
            # if request.POST.has_key('stripe'):
            #     amountInCents = request.POST['order_total_incl_tax_in_cents']
            #     chargeSuccess = chargeSharedOscar(request, basket, order_number, amountInCents)
            #     if not chargeSuccess:
            #         return HttpResponseRedirect(reverse('basket:summary'))

            return self.submit(basket, payment_kwargs=None, order_kwargs=None)


        error_response = self.get_error_response()
        if error_response:
            return error_response

        # if self.preview:
        #     # We use a custom parameter to indicate if this is an attempt to
        #     # place an order.  Without this, we assume a payment form is being
        #     # submitted from the payment-details page
        #     if request.POST.get('action', '') == 'place_order':
        #         return self.submit(request.basket)
        #     return self.render_preview(request)

        # Posting to payment-details isn't the right thing to do
        return self.get(request, *args, **kwargs)

    def get_error_response(self):
        # Check that the user's basket is not empty
        if self.request.basket.is_empty:
            messages.error(self.request, _("You need to add some items to your basket to checkout"))
            return HttpResponseRedirect(reverse('basket:summary'))

        shipping_required = self.request.basket.is_shipping_required()

        shipping_method = self.checkout_session.shipping_method(self.basket)

        try:
            shipping_code = shipping_method.code
        except:
            shipping_code = None


        # Check that shipping address has been completed
        if shipping_required and shipping_code != "local-pickup" and not self.checkout_session.is_shipping_address_set():
        ##if shipping_required and  ##not self.checkout_session.is_shipping_address_set():
            messages.info(self.request, _("Please choose a delivery address"))
            return HttpResponseRedirect(reverse('checkout:shipping-address'))


        # Check that shipping method has been set
        if shipping_required and shipping_code != "local-pickup" and not self.checkout_session.is_shipping_method_set():
            messages.info(self.request, _("Please choose a delivery method"))
            return HttpResponseRedirect(reverse('checkout:shipping-method'))


        # Check that payment method has been set
        if self.preview:
            payment_method = self.checkout_session.payment_method()
            #if shipping_code != "local-pickup" and payment_method == 'in_person':
            #    payment_method = None
            #    self.checkout_session.unset_payment_method()
            if not payment_method:
                messages.info(self.request, _("Please choose a payment method"))
                return HttpResponseRedirect(reverse('checkout:payment-method'))


    def get_context_data(self, **kwargs):
        # Return kwargs directly instead of using 'params' as in django's
        # TemplateView
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)

        # Add guest email if one is set
        ctx['guest_email'] = self.checkout_session.get_guest_email()

        if self.request.basket:
            ctx['basket'] = self.request.basket

        if self.request.basket:
            ctx['mseller'] = getSellerFromOscarID(self.request.basket.seller.user.id)
        ctx['mu'] = getSellerFromOscarID(self.request.user.id)

        ctx['current_sponsored_orgs']= SponsoredOrganization.objects.filter(is_current=True)
        ctx['stripeAppPubKey'] = stripe_keys['publishable_key']
        ctx.update(kwargs)

        pip = settings.PAY_IN_PERSON

        if pip == True or pip == 1:
            ctx['pay_in_person_allowed'] = True
        else:
            ctx['pay_in_person_allowed'] = False
        ctx['test_local'] = settings.TEST_LOCAL

        #if self.request.GET.has_key('pip'):
        #    pip = self.request.GET['pip']
        #    if pip == "hh6ywei22nzl":
        #        ctx['pay_in_person_allowed'] = True

        return ctx

    def get_template_names(self):
        return [self.template_name_preview] if self.preview else [
            self.template_name]

    def render_preview(self, request, **kwargs):
        """
        Show a preview of the order.

        If sensitive data was submitted on the payment details page, you will
        need to pass it back to the view here so it can be stored in hidden form
        inputs.  This avoids ever writing the sensitive data to disk.
        """
        ctx = self.get_context_data()
        ctx.update(kwargs)
        return self.render_to_response(ctx)

    def can_basket_be_submitted(self, basket):
        for line in basket.lines.all():
            is_permitted, reason = line.product.is_purchase_permitted(self.request.user, line.quantity)
            if not is_permitted:
                return False, reason, reverse('basket:summary')
        return True, None, None

    def get_default_billing_address(self):
        """
        Return default billing address for user

        This is useful when the payment details view includes a billing address
        form - you can use this helper method to prepopulate the form.

        Note, this isn't used in core oscar as there is no billing address form
        by default.
        """
        if not self.request.user.is_authenticated():
            return None
        try:
            return self.request.user.addresses.get(is_default_for_billing=True)
        except UserAddress.DoesNotExist:
            return None

    def submit(self, basket, payment_kwargs=None, order_kwargs=None):
        """
        Submit a basket for order placement.

        The process runs as follows:

         * Generate an order number
         * Freeze the basket so it cannot be modified any more (important when
           redirecting the user to another site for payment as it prevents the
           basket being manipulated during the payment process).
         * Attempt to take payment for the order
           - If payment is successful, place the order
           - If a redirect is required (eg PayPal, 3DSecure), redirect
           - If payment is unsuccessful, show an appropriate error message

        :basket: The basket to submit.
        :payment_kwargs: Additional kwargs to pass to the handle_payment method.
        :order_kwargs: Additional kwargs to pass to the place_order method.
        """
        if payment_kwargs is None:
            payment_kwargs = {}
        if order_kwargs is None:
            order_kwargs = {}

        # Domain-specific checks on the basket
        is_valid, reason, url = self.can_basket_be_submitted(basket)
        if not is_valid:
            messages.error(self.request, reason)
            return HttpResponseRedirect(url)

        # We generate the order number first as this will be used
        # in payment requests (ie before the order model has been
        # created).  We also save it in the session for multi-stage
        # checkouts (eg where we redirect to a 3rd party site and place
        # the order on a different request).


        order_number = self.generate_order_number(basket)

        self.checkout_session.set_order_number(order_number)
        logger.info("Order #%s: beginning submission process for basket #%d", order_number, basket.id)

        # Freeze the basket so it cannot be manipulated while the customer is
        # completing payment on a 3rd party site.  Also, store a reference to
        # the basket in the session so that we know which basket to thaw if we
        # get an unsuccessful payment response when redirecting to a 3rd party
        # site.
        self.freeze_basket(basket)
        self.checkout_session.set_submitted_basket(basket)

        # Handle payment.  Any payment problems should be handled by the
        # handle_payment method raise an exception, which should be caught
        # within handle_POST and the appropriate forms redisplayed.
        error_msg = _("A problem occurred while processing payment for this "
                      "order - no payment has been taken.  Please "
                      "contact customer services if this problem persists")
        pre_payment.send_robust(sender=self, view=self)
        total_incl_tax, total_excl_tax = self.get_order_totals(basket)
        try:
            self.handle_payment(order_number, total_incl_tax, **payment_kwargs)
        except RedirectRequired, e:
            # Redirect required (eg PayPal, 3DS)
            logger.info("Order #%s: redirecting to %s", order_number, e.url)
            return HttpResponseRedirect(e.url)
        except UnableToTakePayment, e:
            # Something went wrong with payment but in an anticipated way.  Eg
            # their bankcard has expired, wrong card number - that kind of
            # thing. This type of exception is supposed to set a friendly error
            # message that makes sense to the customer.
            msg = unicode(e)
            logger.warning("Order #%s: unable to take payment (%s) - restoring basket", order_number, msg)
            self.restore_frozen_basket()
            # We re-render the payment details view
            self.preview = False
            return self.render_to_response(self.get_context_data(error=msg))
        except PaymentError, e:
            # A general payment error - Something went wrong which wasn't
            # anticipated.  Eg, the payment gateway is down (it happens), your
            # credentials are wrong - that king of thing.
            # It makes sense to configure the checkout logger to
            # mail admins on an error as this issue warrants some further
            # investigation.
            msg = unicode(e)
            logger.error("Order #%s: payment error (%s)", order_number, msg)
            self.restore_frozen_basket()
            self.preview = False
            return self.render_to_response(self.get_context_data(error=error_msg))
        except Exception, e:
            # Unhandled exception - hopefully, you will only ever see this in
            # development.
            logger.error("Order #%s: unhandled exception while taking payment (%s)", order_number, e)
            logger.exception(e)
            self.restore_frozen_basket()
            self.preview = False
            return self.render_to_response(self.get_context_data(error=error_msg))
        post_payment.send_robust(sender=self, view=self)

        # If all is ok with payment, try and place order
        logger.info("Order #%s: payment successful, placing order", order_number)
        try:
            return self.handle_order_placement(
                order_number, basket, total_incl_tax, total_excl_tax,
                **order_kwargs)
        except UnableToPlaceOrder, e:
            # It's possible that something will go wrong while trying to
            # actually place an order.  Not a good situation to be in as a
            # payment transaction may already have taken place, but needs
            # to be handled gracefully.
            logger.error("Order #%s: unable to place order - %s",
                         order_number, e)
            logger.exception(e)
            msg = unicode(e)
            self.restore_frozen_basket()
            return self.render_to_response(self.get_context_data(error=msg))

    def generate_order_number(self, basket):
        """
        Return a new order number
        """
        return OrderNumberGenerator().order_number(basket)

    def freeze_basket(self, basket):
        """
        Freeze the basket so it can no longer be modified
        """
        # We freeze the basket to prevent it being modified once the payment
        # process has started.  If your payment fails, then the basket will
        # need to be "unfrozen".  We also store the basket ID in the session
        # so the it can be retrieved by multistage checkout processes.
        basket.freeze()

    def handle_payment(self, order_number, total, **kwargs):
        """
        Handle any payment processing and record payment sources and events.

        This method is designed to be overridden within your project.  The
        default is to do nothing as payment is domain-specific.

        This method is responsible for handling payment and recording the
        payment sources (using the add_payment_source method) and payment
        events (using add_payment_event) so they can be
        linked to the order when it is saved later on.
        """

        payment_method = self.checkout_session.payment_method()

        if payment_method == "in_person":

            source_type, _ = SourceType.objects.get_or_create(name='in_person')
            source = Source(source_type=source_type,
                            currency=settings.OSCAR_DEFAULT_CURRENCY,
                            amount_allocated=total,
                            reference=order_number)
            self.add_payment_source(source)

            # Also record payment event
            self.add_payment_event(
                'paid', total, reference=order_number)

            pass

        if payment_method == "stripe":
            from apps.homemade.homeMade import chargeSharedOscar
            from math import floor, ceil
            if self.request.POST.has_key('stripe'):
                amountInCents = int(floor(float(total) * 100.0))

                ## depending on the shipping choices, shipping may be paid by website or by the seller
                shippingCost = float(self.checkout_session.shipping_method().basket_charge_excl_tax())

                if self.checkout_session.shipping_method().shippingPaidBySeller():
                    shippingCostToSeller = shippingCost
                    shippingCostToSite = 0.0
                else:
                    shippingCostToSite = shippingCost
                    shippingCostToSeller = 0.0

                if shippingCost > float(total):
                    errMsg = "There is a problem with the payment parameters. Please contact website support about error 678. Thank you."
                    messages.error(self.request, errMsg)
                    return HttpResponseRedirect(reverse('checkout:preview'))

                total_incl_tax, total_excl_tax = self.get_order_totals()
                totalWithoutShippingExclTax = float(total_excl_tax) - shippingCostToSite - shippingCostToSeller
                totalWithoutShippingInclTax = float(total_incl_tax) - shippingCostToSite - shippingCostToSeller
                #totalExclTaxCents =  int(floor(float(total_excl_tax) * 100.0))  

                ## start over

                tot1 = float(total_excl_tax)

                #amountToSeller = (tot1 * (1. - 0.035) - 0.3) / 1.029
                #tax = float(total_incl_tax) - float(total_excl_tax)

                #amountGoingToSellerInCents = int(round(float(amountToSeller) * 100.0))

                stripeFee = (0.029 * float(total) ) + 0.30
                stripeFeeInCents = int(round(float(stripeFee) * 100.0))
                print "to stripe: " + str(float(stripeFee) * 100.0)

                fee = 0.035 * float(totalWithoutShippingExclTax) 
                feeInCents = int(round(float(fee) * 100.0))

                feePossiblyWithShipping = fee + shippingCostToSite
                
                ## using magic number to avoid charging a fee that is too large when 10.5 for example, 
                ## don't want to round up in that case
                feePossiblyWithShippingInCents = int(round(float(feePossiblyWithShipping) * 100.0 - 0.00001))

                print "fee: " + str(float(feePossiblyWithShipping) * 100.0)

                totalInCents = int(round(float(totalWithoutShippingInclTax) * 100.0))
                amountUsedByStripeForFeeCalc = totalInCents - feePossiblyWithShippingInCents

                #amountGoingToSellerInCents = int(round(float(totalWithoutShippingInclTax) * 100.0))
                #amountGoingToSellerInCents = amountGoingToSellerInCents - feeInCents - stripeFeeInCents

                amountGoingToSellerInCents = amountInCents - stripeFeeInCents - feePossiblyWithShippingInCents

                #amountToSeller = float(total) - stripeFee - feePossiblyWithShipping
                #amountGoingToSellerInCents = int(round(float(amountToSeller) * 100.0))
                print "Seller: " + str(amountGoingToSellerInCents)

                ## assert that total is correct
                tot = amountGoingToSellerInCents + feePossiblyWithShippingInCents + stripeFeeInCents
                tot2 = int(float(total_incl_tax) * 100.0)


                
                if tot != tot2:
                    errMsg = "There is a problem with the payment parameters. Please contact website support about error 684. Thank you."
                    messages.error(self.request, errMsg)
                    print str(tot) + "  " + str(tot2)
                    print amountGoingToSellerInCents
                    print feePossiblyWithShippingInCents
                    print stripeFeeInCents
                    #return HttpResponseRedirect(reverse('checkout:preview'))


                chargeResponse = chargeSharedOscar(self.request, self.request.basket, order_number, amountInCents, feePossiblyWithShippingInCents)
                try:
                    chargeSuccess = not chargeResponse.failure_code 
                except:
                    chargeSuccess = False
                if not chargeSuccess:
                    return HttpResponseRedirect(reverse('checkout:preview'))

            stripe_ref = chargeResponse.id
            # Request was successful - record the "payment source".  As this
            # request was a 'pre-auth', we set the 'amount_allocated' - if we had
            # performed an 'auth' request, then we would set 'amount_debited'.
            source_type, _ = SourceType.objects.get_or_create(name='Stripe')
            source = Source(source_type=source_type,
                            currency=settings.OSCAR_DEFAULT_CURRENCY,
                            amount_allocated=total,
                            reference=stripe_ref)
            self.add_payment_source(source)

            # Also record payment event
            self.add_payment_event(
                'paid', total, reference=stripe_ref)
        # else:
        #     print "Assuming paying local"
        #     source_type, _ = SourceType.objects.get_or_create(name=payment_method)
        #     source = Source(source_type=source_type,
        #                     currency=settings.OSCAR_DEFAULT_CURRENCY,
        #                     amount_allocated=total,
        #                     reference=order.id)

        return


# =========
# Thank you
# =========


class ThankYouView(DetailView):
    """
    Displays the 'thank you' page which summarises the order just submitted.
    """
    template_name = 'checkout/thank_you.html'
    context_object_name = 'order'

    def get_object(self):
        # We allow superusers to force an order thankyou page for testing
        order = None
        if self.request.user.is_superuser:
            if 'order_number' in self.request.GET:
                order = Order._default_manager.get(number=self.request.GET['order_number'])
            elif 'order_id' in self.request.GET:
                order = Order._default_manager.get(id=self.request.GET['orderid'])

        if not order:
            if 'checkout_order_id' in self.request.session:
                order = Order._default_manager.get(pk=self.request.session['checkout_order_id'])
            else:
                raise Http404(_("No order found"))

        return order
