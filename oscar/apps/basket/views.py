from urlparse import urlparse

from django.contrib import messages
from django.template.loader import render_to_string
from django.template import RequestContext
from django.core.urlresolvers import reverse, resolve
from django.utils import simplejson as json
from django.db.models import get_model
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.views.generic import FormView, View, ListView
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from extra_views import ModelFormSetView
from oscar.core import ajax
from oscar.apps.basket.signals import basket_addition, voucher_addition
from oscar.templatetags.currency_filters import currency
from oscar.core.loading import get_class, get_classes
Applicator = get_class('offer.utils', 'Applicator')
(BasketLineForm, AddToBasketForm, BasketVoucherForm,
 SavedLineFormSet, SavedLineForm, ProductSelectionForm) = get_classes(
     'basket.forms', ('BasketLineForm', 'AddToBasketForm',
                      'BasketVoucherForm', 'SavedLineFormSet',
                      'SavedLineForm', 'ProductSelectionForm'))
Repository = get_class('shipping.repository', ('Repository'))

from django.contrib.sites.models import Site, get_current_site

Basket = get_model('basket', 'basket')
CommunicationEvent = get_model('order', 'CommunicationEvent')
CommunicationEventType = get_model('customer', 'CommunicationEventType')

Dispatcher = get_class('customer.utils', 'Dispatcher')

# Standard logger for checkout events
import logging
logger = logging.getLogger('oscar.checkout')

from decimal import Decimal
from django.conf import settings
from oscar.apps.basket.middleware import BasketMiddleware



from oscar.apps.order.models import SponsoredOrganization

def get_messages(basket, offers_before, offers_after,
                 include_buttons=True):
    """
    Return the messages about offer changes
    """
    # Look for changes in offers
    offers_lost = set(offers_before.keys()).difference(
        set(offers_after.keys()))
    offers_gained = set(offers_after.keys()).difference(
        set(offers_before.keys()))

    # Build a list of (level, msg) tuples
    offer_messages = []
    for offer_id in offers_lost:
        offer = offers_before[offer_id]
        msg = render_to_string(
            'basket/messages/offer_lost.html',
            {'offer': offer})
        offer_messages.append((
            messages.WARNING, msg))
    for offer_id in offers_gained:
        offer = offers_after[offer_id]
        msg = render_to_string(
            'basket/messages/offer_gained.html',
            {'offer': offer})
        offer_messages.append((
            messages.SUCCESS, msg))

    # We use the 'include_buttons' parameter to determine whether to show the
    # 'Checkout now' buttons.  We don't want to show these on the basket page.
    msg = render_to_string(
        'basket/messages/new_total.html',
        {'basket': basket,
         'include_buttons': include_buttons})
    offer_messages.append((
        messages.INFO, msg))

    return offer_messages


def apply_messages(request, offers_before):
    """
    Set flash messages triggered by changes to the basket
    """
    # Re-apply offers to see if any new ones are now available
    request.basket.reset_offer_applications()
    Applicator().apply(request, request.basket)
    offers_after = request.basket.applied_offers()

    for level, msg in get_messages(
            request.basket, offers_before, offers_after):
        messages.add_message(
            request, level, msg, extra_tags='safe noicon')


class BasketView(ModelFormSetView):
    model = get_model('basket', 'Line')
    basket_model = get_model('basket', 'Basket')
    form_class = BasketLineForm
    extra = 0
    can_delete = True
    template_name = 'basket/basket.html'

    def __init__(self):

       super(BasketView, self).__init__()
       return


    def post(self, request, *args, **kwargs):
        ## should throw some exceptions?

        if not request.POST.has_key('basket_id'):
            return self.get(request, **kwargs)
        basket = Basket.objects.filter(id=request.POST['basket_id'])[0]

        ## seller sets the shipping cost/quote for a basket
        if request.POST.has_key('ship_cost'):
            shipCost = request.POST.get('ship_cost')
            shipping_info = basket.shipping_info
            if shipping_info:
                shipDict = json.loads(shipping_info)
            else:
                shipDict = {}
            shipDict['needNewEstimate'] = False
            shipDict['customShipAmount'] = shipCost
            shipDict['query-seller'] = shipCost

            basket.shipping_info = json.dumps(shipDict)
            ## freeze basket if need a shipping estimate
            #basket.freeze()
            basket.save()

            ## set the shipping cost, then go back to same page, 
            ##    with success message that is set, msg sent to buyer
            msg = _("The total shipping cost for this basket has been set to  " + str(shipCost))
                        
            messages.success(request, msg)


            ## send a message to the buyer 
            self.sendMessageAboutQuoteToBuyer(request, basket, shipCost)
    
            ##return HttpResponseRedirect(reverse('catalogue:index'))
            return self.get(request, *args, **kwargs)


    def sendMessageAboutQuoteToBuyer(self, request, basket, shipCost):
        seller = basket.seller

        ## send the email to buyer with a link to the checkout
 

        # sellerUser = seller.user

        buyerUser = basket.owner

        ctx = {'user': self.request.user,
               'basket': basket,
               'site': get_current_site(self.request),
               'lines': basket.lines.all()}

        site = Site.objects.get_current()
        path = reverse('checkout:preview') + "?basket_id=" + str(basket.id)

        ctx['continueCheckoutUrl'] = 'http://%s%s' % (site.domain, path)
        ctx['basket_total'] = basket.total_incl_tax
        ctx['shipCost'] = shipCost
        ctx['orderTotal'] = Decimal(float(shipCost) + float(basket.total_incl_tax))

        #shipAddressId = self.checkout_session.shipping_user_address_id()
        #if shipAddressId:
        #    shipAddress = UserAddress.objects.get(id=shipAddressId)
        #else:
        shipAddress = None
        ctx['shipping_address'] = shipAddress


        messages = CommunicationEventType.objects.get_and_render('SHIP_QUOTE_BUYER', ctx)
        event_type = None

        if messages and messages['body']:
            #logger.info("Order #%s - sending %s messages", order.number, code)
            dispatcher = Dispatcher(logger)
            dispatcher.dispatch_user_messages(buyerUser, messages,
                                               event_type)

        return True


    def get(self, request, *args, **kwargs):
        if request.GET.has_key('basket_id'):
            try:
                self.basket = Basket.objects.filter(id=request.GET['basket_id'])[0]
                request.basket = self.basket
            except:
                ## ignore input, give default basket from request. Could also check that basket is for user here
                pass

        return super(BasketView, self).get(request, *args, **kwargs)        


    def get_queryset(self):
        return self.request.basket.all_lines()

    def get_shipping_methods(self, basket):
        return Repository().get_shipping_methods(
            self.request.user, self.request.basket)

    def get_default_shipping_method(self, basket):
        return Repository().get_default_shipping_method(
            self.request.user, self.request.basket)

    def get_basket_warnings(self, basket):
        """
        Return a list of warnings that apply to this basket
        """
        warnings = []
        for line in basket.all_lines():
            warning = line.get_warning()
            if warning:
                warnings.append(warning)
        return warnings

    def get_upsell_messages(self, basket):
        offers = Applicator().get_offers(self.request, basket)
        applied_offers = basket.offer_applications.offers.values()
        msgs = []
        for offer in offers:
            if offer.is_condition_partially_satisfied(basket) and offer not in applied_offers:
                data = {
                    'message': offer.get_upsell_message(basket),
                    'offer': offer}
                msgs.append(data)
        return msgs

    def get_context_data(self, **kwargs):
        context = super(BasketView, self).get_context_data(**kwargs)
        context['voucher_form'] = BasketVoucherForm()

        # Shipping information is included to give an idea of the total order
        # cost.  It is also important for PayPal Express where the customer
        # gets redirected away from the basket page and needs to see what the
        # estimated order total is beforehand.
        #method = self.get_default_shipping_method(self.request.basket)
        #context['shipping_method'] = method
        #context['shipping_methods'] = self.get_shipping_methods(
        #    self.request.basket)
        context['order_total_incl_tax'] = (
            self.request.basket.total_incl_tax) #+
            ##method.basket_charge_incl_tax())
        context['order_total_incl_tax_in_cents'] = int(100.0 * float(
            self.request.basket.total_incl_tax)) #+
            ##method.basket_charge_incl_tax()))
        context['basket_warnings'] = self.get_basket_warnings(
            self.request.basket)
        context['upsell_messages'] = self.get_upsell_messages(
            self.request.basket)

        if self.request.user.is_authenticated():
            try:
                saved_basket = self.basket_model.saved.get(
                    owner=self.request.user)
            except self.basket_model.DoesNotExist:
                pass
            else:
                if not saved_basket.is_empty:
                    saved_queryset = saved_basket.all_lines().select_related(
                        'product', 'product__stockrecord')
                    formset = SavedLineFormSet(user=self.request.user,
                                               basket=self.request.basket,
                                               queryset=saved_queryset,
                                               prefix='saved')
                    context['saved_formset'] = formset
        return context

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', reverse('basket:list'))

    def formset_valid(self, formset):
        # Store offers before any changes are made so we can inform the user of
        # any changes
        offers_before = self.request.basket.applied_offers()
        save_for_later = False


        print self.request.POST
        # Keep a list of messages - we don't immediately call
        # django.contrib.messages as we may be returning an AJAX response in
        # which case we pass the messages back in a JSON payload.
        flash_messages = ajax.FlashMessages()

        for form in formset:
            if (hasattr(form, 'cleaned_data') and
                    form.cleaned_data['save_for_later']):
                line = form.instance
                if self.request.user.is_authenticated():
                    self.move_line_to_saved_basket(line)

                    msg = render_to_string(
                        'basket/messages/line_saved.html',
                        {'line': line})
                    flash_messages.info(msg)

                    save_for_later = True
                else:
                    msg = _("You can't save an item for later if you're "
                            "not logged in!")
                    messages.error(self.request, msg)
                    return HttpResponseRedirect(self.get_success_url())

        if save_for_later:
            # No need to call super if we're moving lines to the saved basket
            response = HttpResponseRedirect(self.get_success_url())
        else:
            # Save changes to basket as per normal
            response = super(BasketView, self).formset_valid(formset)

        # If AJAX submission, don't redirect but reload the basket content HTML
        if self.request.is_ajax():
            # Reload basket and apply offers again
            self.request.basket = get_model('basket', 'Basket').objects.get(
                id=self.request.basket.id)
            Applicator().apply(self.request, self.request.basket)
            offers_after = self.request.basket.applied_offers()

            for level, msg in get_messages(
                    self.request.basket, offers_before,
                    offers_after, include_buttons=False):
                flash_messages.add_message(level, msg)

            # Reload formset - we have to remove the POST fields from the
            # kwargs as, if they are left in, the formset won't construct
            # correctly as there will be a state mismatch between the
            # management form and the database.
            kwargs = self.get_formset_kwargs()
            del kwargs['data']
            del kwargs['files']
            if 'queryset' in kwargs:
                del kwargs['queryset']
            formset = self.get_formset()(queryset=self.get_queryset(),
                                         **kwargs)
            ctx = self.get_context_data(formset=formset,
                                        basket=self.request.basket)
            
            response = HttpResponseRedirect(self.get_success_url())
            return response
            #return self.json_response(ctx, flash_messages)

        apply_messages(self.request, offers_before)

        return response

    def json_response(self, ctx, flash_messages):
        basket_html = render_to_string(
            'basket/partials/basket_content.html',
            RequestContext(self.request, ctx))
        payload = {
            'content_html': basket_html,
            'messages': flash_messages.to_json()}
        return HttpResponse(json.dumps(payload),
                            mimetype="application/json")

    def move_line_to_saved_basket(self, line):
        saved_basket, _ = get_model('basket', 'basket').saved.get_or_create(
            owner=self.request.user)
        saved_basket.merge_line(line)

    def formset_invalid(self, formset):
        flash_messages = ajax.FlashMessages()
        flash_messages.warning(_("Your basket couldn't be updated"))

        if self.request.is_ajax():
            ctx = self.get_context_data(formset=formset,
                                        basket=self.request.basket)
            return self.json_response(ctx, flash_messages)

        flash_messages.apply_to_request(self.request)
        return super(BasketView, self).formset_invalid(formset)

class BasketListView(ListView):
    """
    A list of baskets
    """
    context_object_name = "baskets"
    template_name = 'basket/basket_multi.html'
    model = Basket
    q = None
    pq = None


    def get(self, request, *args, **kwargs):

        return super(BasketListView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        ## should throw some exceptions?

        if not request.POST.has_key('basket_id'):
            return self.get(request, **kwargs)
        try:
            basket = Basket.objects.filter(id=request.POST['basket_id'])[0]
        except:
            return self.get(request, **kwargs)
            
        if request.POST.has_key('setSponsoredOrg'):
            sOrg = SponsoredOrganization.objects.filter(id=request.POST['sponsored_org_id'])[0]
            basket.sponsored_org = sOrg
            basket.save()
        if request.POST.has_key('unsetSponsoredOrg'):    
            basket.sponsored_org = None
            basket.save()
        if request.POST.has_key('remove-line'):
            try:
                basket.lines.get(id=request.POST['line_id']).delete()
                ## if last line, delete basket or make default
                if not len(basket.lines.all()):
                    #if len(Basket.objects.filter(status="Open"))  == 1:
                    #    basket.seller = None
                    #else:
                    ## hack ,fix later
                    try:
                        self.request.session['checkout_data'+"_" + str(basket.id)] = {}
                        
                    except:
                        pass
                    basket.delete()
            except:
                "line not deleted"
        if request.POST.has_key('update-quantity'):
            try:
                cur_line = basket.lines.get(id=request.POST['line_id'])
                cur_line.quantity = request.POST['quantity']
                cur_line.save()

                print request.POST['quantity']
                basket.save()
            except:
                "line not deleted"            



        # if request.POST.has_key('place-order'):

        #     from oscar.apps.checkout.views import  PaymentDetailsView
        #     pdv = PaymentDetailsView(request=request)
        #     return pdv.submit(basket, payment_kwargs=None, order_kwargs=None)

        return self.get(request, **kwargs)


    def get_search_query(self):
        q = self.request.GET.get('q', None)
        self.q =  q.strip() if q else None
        pq = self.request.GET.get('booth', None)
        self.pq = pq.strip() if pq else None
        return 

  

    def get_context_data(self, **kwargs):
        context = super(BasketListView, self).get_context_data(**kwargs)
        #self.get_search_query()
        #q = self.q
        #pq = self.pq

        if self.request.user.is_authenticated():
            baskets = Basket.objects.filter(owner=self.request.user, status="Open").order_by('-id')
        else:
##            import ipdb;ipdb.set_trace()
            ## get baskets from the cookies
            bm = BasketMiddleware()
            cookie_basket = bm.get_cookie_basket(settings.OSCAR_BASKET_COOKIE_OPEN, self.request, Basket.open)
            cookie_baskets = bm.get_cookie_baskets(settings.OSCAR_BASKET_COOKIE_OPEN + 's', self.request, Basket.open)
            baskets = cookie_baskets            

        context['baskets'] = baskets
        context['current_sponsored_orgs']= SponsoredOrganization.objects.filter(status__icontains='current')
        ## give context for each of the baskets?? Or just set it in the damn model


        return context




class BasketAddView(FormView):
    """
    Handles the add-to-basket operation, shouldn't be accessed via
    GET because there's nothing sensible to render.
    """
    form_class = AddToBasketForm
    product_select_form_class = ProductSelectionForm
    product_model = get_model('catalogue', 'product')
    add_signal = basket_addition

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('basket:summary'))

    def get_form_kwargs(self):
        kwargs = super(BasketAddView, self).get_form_kwargs()
        product_select_form = self.product_select_form_class(self.request.POST)

        if product_select_form.is_valid():
            kwargs['instance'] = product_select_form.cleaned_data['product_id']
        else:
            kwargs['instance'] = None
        kwargs['request'] = self.request
        return kwargs

    def get_success_url(self):
        url = None
        if self.request.POST.get('next'):
            url = self.request.POST.get('next')
        elif 'HTTP_REFERER' in self.request.META:
            url = self.request.META['HTTP_REFERER']
        if url:
            # We only allow internal URLs so we see if the url resolves
            try:
                resolve(urlparse(url).path)
            except Http404:
                url = None
        if url is None:
            url = reverse('basket:summary')
        return url

    def form_valid(self, form):

        ## check if there exists a basket for this seller. If not, create one.
        print "form.instance"
        print form.instance

        partner = form.instance.stockrecord.partner

        bask = None
        bb = None ## query for basket
        if self.request.user.is_authenticated():        
            try:
                bb = Basket.objects.filter(owner=self.request.user, status="Open", seller=partner)
            except:
                bb = None
        else:
            ## anonymous buyer
            if self.request.basket.seller == partner:
                bask = self.request.basket
            else:
                bm = BasketMiddleware()
                cookie_baskets = bm.get_cookie_baskets(settings.OSCAR_BASKET_COOKIE_OPEN + 's', self.request, Basket.open)
                for b in cookie_baskets:
                    try:
                        if b.seller == partner:
                            bask = b
                            break
                    except:
                        pass


        if bask == None:
            if (bb == None or len(bb) == 0) and bask == None:

                ## take the default basket if possible
                if self.request.basket.seller == None:
                    self.request.basket.seller = partner
                    bask = self.request.basket
                    bask.save()
                else:   
                    ## create a new one
                    #bask = Basket(owner=self.request.user, status="Open", seller=partner)
                    bask = Basket(status="Open", seller=partner)                    
                    if self.request.user.is_authenticated():
                        bask.owner = self.request.user
                        bask.save()
                    else:
                        ## add to the cookies 
                        r = 9

            elif len(bb) == 1:  
                bask = bb[0]
            else:
                ## should not happen!!! merge 'em
                pass
            bask.save()

        ## set the current basket to be the default basket in the request
        self.request.basket = bask
        print "SELLER"
        print bask.id
        print self.request.basket.seller

        offers_before = bask.applied_offers()


        bask.add_product(
            form.instance, form.cleaned_data['quantity'],
            form.cleaned_options())

        messages.success(self.request, self.get_success_message(form),
                         extra_tags='safe noicon')

        # Check for additional offer messages
        apply_messages(self.request, offers_before)

        # Send signal for basket addition
        self.add_signal.send(
            sender=self, product=form.instance, user=self.request.user)

        return super(BasketAddView, self).form_valid(form)

    def get_success_message(self, form):
        return render_to_string(
            'basket/messages/addition.html',
            {'product': form.instance,
             'quantity': form.cleaned_data['quantity']})

    def form_invalid(self, form):
        msgs = []
        for error in form.errors.values():
            msgs.append(error.as_text())
        messages.error(self.request, ",".join(msgs))
        return HttpResponseRedirect(
            self.request.META.get('HTTP_REFERER', reverse('basket:summary')))


class VoucherAddView(FormView):
    form_class = BasketVoucherForm
    voucher_model = get_model('voucher', 'voucher')
    add_signal = voucher_addition

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('basket:summary'))

    def apply_voucher_to_basket(self, voucher):
        if not voucher.is_active():
            messages.error(
                self.request,
                _("The '%(code)s' voucher has expired") % {
                    'code': voucher.code})
            return

        is_available, message = voucher.is_available_to_user(self.request.user)
        if not is_available:
            messages.error(self.request, message)
            return

        self.request.basket.vouchers.add(voucher)

        # Raise signal
        self.add_signal.send(sender=self,
                             basket=self.request.basket,
                             voucher=voucher)

        # Recalculate discounts to see if the voucher gives any
        Applicator().apply(self.request, self.request.basket)
        discounts_after = self.request.basket.offer_applications

        # Look for discounts from this new voucher
        found_discount = False
        for discount in discounts_after:
            if discount['voucher'] and discount['voucher'] == voucher:
                found_discount = True
                break
        if not found_discount:
            messages.warning(
                self.request,
                _("Your basket does not qualify for a voucher discount"))
            self.request.basket.vouchers.remove(voucher)
        else:
            messages.info(
                self.request,
                _("Voucher '%(code)s' added to basket") % {
                    'code': voucher.code})

    def form_valid(self, form):
        code = form.cleaned_data['code']
        if not self.request.basket.id:
            return HttpResponseRedirect(
                self.request.META.get('HTTP_REFERER',
                                      reverse('basket:summary')))
        if self.request.basket.contains_voucher(code):
            messages.error(
                self.request,
                _("You have already added the '%(code)s' voucher to "
                  "your basket") % {'code': code})
        else:
            try:
                voucher = self.voucher_model._default_manager.get(code=code)
            except self.voucher_model.DoesNotExist:
                messages.error(
                    self.request,
                    _("No voucher found with code '%(code)s'") % {
                        'code': code})
            else:
                self.apply_voucher_to_basket(voucher)
        return HttpResponseRedirect(
            self.request.META.get('HTTP_REFERER', reverse('basket:summary')))

    def form_invalid(self, form):
        messages.error(self.request, _("Please enter a voucher code"))
        return HttpResponseRedirect(reverse('basket:summary') + '#voucher')


class VoucherRemoveView(View):
    voucher_model = get_model('voucher', 'voucher')

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('basket:summary'))

    def post(self, request, *args, **kwargs):
        voucher_id = int(kwargs.pop('pk'))
        if not request.basket.id:
            # Hacking attempt - the basket must be saved for it to have
            # a voucher in it.
            return HttpResponseRedirect(reverse('basket:summary'))
        try:
            voucher = request.basket.vouchers.get(id=voucher_id)
        except ObjectDoesNotExist:
            messages.error(
                request, _("No voucher found with id '%d'") % voucher_id)
        else:
            request.basket.vouchers.remove(voucher)
            request.basket.save()
            messages.info(
                request, _("Voucher '%s' removed from basket") % voucher.code)
        return HttpResponseRedirect(reverse('basket:summary'))


class SavedView(ModelFormSetView):
    model = get_model('basket', 'line')
    basket_model = get_model('basket', 'basket')
    formset_class = SavedLineFormSet
    form_class = SavedLineForm
    extra = 0
    can_delete = True

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('basket:summary'))

    def get_queryset(self):
        try:
            saved_basket = self.basket_model.saved.get(owner=self.request.user)
            return saved_basket.all_lines().select_related(
                'product', 'product__stockrecord')
        except self.basket_model.DoesNotExist:
            return []

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', reverse('basket:summary'))

    def get_formset_kwargs(self):
        kwargs = super(SavedView, self).get_formset_kwargs()
        kwargs['prefix'] = 'saved'
        kwargs['basket'] = self.request.basket
        kwargs['user'] = self.request.user
        return kwargs

    def formset_valid(self, formset):
        offers_before = self.request.basket.applied_offers()

        is_move = False
        for form in formset:
            if form.cleaned_data.get('move_to_basket', False):
                is_move = True
                msg = render_to_string(
                    'basket/messages/line_restored.html',
                    {'line': form.instance})
                messages.info(self.request, msg, extra_tags='safe noicon')
                real_basket = self.request.basket
                real_basket.merge_line(form.instance)

        if is_move:
            # As we're changing the basket, we need to check if it qualifies
            # for any new offers.
            apply_messages(self.request, offers_before)
            response = HttpResponseRedirect(self.get_success_url())
        else:
            response = super(SavedView, self).formset_valid(formset)
        return response

    def formset_invalid(self, formset):
        messages.error(
            self.request,
            '\n'.join(
                error for ed in formset.errors for el
                in ed.values() for error in el))
        return HttpResponseRedirect(
            self.request.META.get('HTTP_REFERER', reverse('basket:summary')))
