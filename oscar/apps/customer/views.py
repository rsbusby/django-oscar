from django.shortcuts import get_object_or_404
from django.views.generic import (TemplateView, ListView, DetailView,
                                  CreateView, UpdateView, DeleteView,
                                  FormView, RedirectView)
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, Http404
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.contrib.auth import (authenticate, login as auth_login,
                                 logout as auth_logout)
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.sites.models import get_current_site
from django.conf import settings
from django.db.models import get_model

from oscar.views.generic import PostActionMixin
from oscar.apps.customer.utils import get_password_reset_url
from oscar.core.loading import get_class, get_profile_class, get_classes
#from oscar.core.compat import get_user_model
from oscar.apps.customer.models import get_user_model
from apps.homemade.homeMade import Seller

## for getting shipping labels
import json
import easypost




##Seller = get_model('homemade', 'Seller')


Dispatcher = get_class('customer.utils', 'Dispatcher')
EmailAuthenticationForm, EmailUserCreationForm, SearchByDateRangeForm = get_classes(
    'customer.forms', ['EmailAuthenticationForm', 'EmailUserCreationForm',
                       'SearchByDateRangeForm'])
ProfileForm = get_class('customer.forms', 'ProfileForm')
UserAddressForm = get_class('address.forms', 'UserAddressForm')
user_registered = get_class('customer.signals', 'user_registered')
Order = get_model('order', 'Order')
Line = get_model('basket', 'Line')
OrderLine = get_model('order', 'Line')
Basket = get_model('basket', 'Basket')
UserAddress = get_model('address', 'UserAddress')
Email = get_model('customer', 'Email')
UserAddress = get_model('address', 'UserAddress')
CommunicationEventType = get_model('customer', 'CommunicationEventType')
ProductAlert = get_model('customer', 'ProductAlert')

ParcelForm = get_class('customer.forms', 'ParcelForm')
ParcelFormSet = get_class('customer.forms', 'ParcelFormSet')


User = get_user_model()


class LogoutView(RedirectView):
    url = reverse_lazy('promotions:home')
    permanent = False

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        response = super(LogoutView, self).get(request, *args, **kwargs)

        for cookie in settings.OSCAR_COOKIES_DELETE_ON_LOGOUT:
            response.delete_cookie(cookie)

        return response


class ProfileUpdateView(FormView):
    form_class = ProfileForm
    template_name = 'customer/profile_form.html'
    communication_type_code = 'EMAIL_CHANGED'

    def get_form_kwargs(self):
        kwargs = super(ProfileUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Grab current user instance before we save form.  We may need this to
        # send a warning email if the email address is changed.
        try:
            old_user = User.objects.get(id=self.request.user.id)
        except User.DoesNotExist:
            old_user = None

        form.save()

        # We have to look up the email address from the form's
        # cleaned data because the object created by form.save() can
        # either be a user or profile depending on AUTH_PROFILE_MODULE
        new_email = form.cleaned_data['email']
        if old_user and new_email != old_user.email:
            # Email address has changed - send a confirmation email to the old
            # address including a password reset link in case this is a
            # suspicious change.
            ctx = {
                'user': self.request.user,
                'site': get_current_site(self.request),
                'reset_url': get_password_reset_url(old_user),
                'new_email': new_email,
            }
            msgs = CommunicationEventType.objects.get_and_render(
                code=self.communication_type_code, context=ctx)
            Dispatcher().dispatch_user_messages(old_user, msgs)

        messages.success(self.request, "Profile updated")
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('customer:summary')


class AccountSummaryView(TemplateView):
    template_name = 'customer/profile.html'

    def get_context_data(self, **kwargs):
        ctx = super(AccountSummaryView, self).get_context_data(**kwargs)
        # Delegate data fetching to separate methods so they are easy to
        # override.
        ctx['addressbook_size'] = self.request.user.addresses.all().count()
        ctx['default_shipping_address'] = self.get_default_shipping_address(
            self.request.user)
        ctx['default_billing_address'] = self.get_default_billing_address(
            self.request.user)
        ctx['orders'] = self.get_orders(self.request.user)
        ctx['sales'] = self.get_sales(self.request.user)
        ctx['emails'] = self.get_emails(self.request.user)
        ctx['sent_emails'] = self.get_sent_emails(self.request.user)        
        ctx['alerts'] = self.get_product_alerts(self.request.user)
        ctx['profile_fields'] = self.get_profile_fields(self.request.user)

        ctx['active_tab'] = self.request.GET.get('tab', 'profile')
        return ctx

    def get_orders(self, user):
        return Order._default_manager.filter(user=user)[0:5]

    def get_sales(self, user):
        basketsForThisSeller = Basket.objects.filter(seller__user=user)
        basketIds = [b.id for b in basketsForThisSeller]
        sales = Order._default_manager.filter(basket_id__in=basketIds)
        return sales[0:5]

    def get_profile_fields(self, user):
        field_data = []

        # Check for custom user model
        for field_name in User._meta.additional_fields:
            field_data.append(
                self.get_model_field_data(user, field_name))

        # Check for profile class
        profile_class = get_profile_class()
        if profile_class:
            try:
                profile = profile_class.objects.get(user=user)
            except ObjectDoesNotExist:
                profile = profile_class(user=user)

            field_names = [f.name for f in profile._meta.local_fields]
            for field_name in field_names:
                if field_name in ('user', 'id'):
                    continue
                field_data.append(
                    self.get_model_field_data(profile, field_name))

        return field_data

    def get_model_field_data(self, model_class, field_name):
        """
        Extract the verbose name and value for a model's field value
        """
        field = model_class._meta.get_field(field_name)
        if field.choices:
            value = getattr(model_class, 'get_%s_display' % field_name)()
        else:
            value = getattr(model_class, field_name)
        return {
            'name': getattr(field, 'verbose_name'),
            'value': value,
        }

    def post(self, request, *args, **kwargs):
        # A POST means an attempt to change the status of an alert
        if 'cancel_alert' in request.POST:
            return self.cancel_alert(request.POST.get('cancel_alert'))
        return super(AccountSummaryView, self).post(request, *args, **kwargs)

    def cancel_alert(self, alert_id):
        try:
            alert = ProductAlert.objects.get(user=self.request.user, pk=alert_id)
        except ProductAlert.DoesNotExist:
            messages.error(self.request, _("No alert found"))
        else:
            alert.cancel()
            messages.success(self.request, _("Alert cancelled"))
        return HttpResponseRedirect(
            reverse('customer:summary')+'?tab=alerts'
        )
   
    def get_sent_emails(self, user):
        return Email.objects.filter(sender=user)

    def get_emails(self, user):
        return Email.objects.filter(user=user)

    def get_product_alerts(self, user):
        return ProductAlert.objects.select_related().filter(
            user=self.request.user,
            date_closed=None,
        )

    def get_default_billing_address(self, user):
        return self.get_user_address(user, is_default_for_billing=True)

    def get_default_shipping_address(self, user):
        return self.get_user_address(user, is_default_for_shipping=True)

    def get_user_address(self, user, **filters):
        try:
            return user.addresses.get(**filters)
        except UserAddress.DoesNotExist:
            return None


class RegisterUserMixin(object):
    communication_type_code = 'REGISTRATION'

    def register_user(self, form):
        """
        Create a user instance and send a new registration email (if configured
        to).
        """
        user = form.save()

        if getattr(settings, 'OSCAR_SEND_REGISTRATION_EMAIL', True):
            self.send_registration_email(user)

        # Raise signal
        user_registered.send_robust(sender=self, user=user)

        print("registering user !!!")
        # We have to authenticate before login
        try:
            user = authenticate(
                username=user.email,
                password=form.cleaned_data['password1'])
        except User.MultipleObjectsReturned:
            # Handle race condition where the registration request is made
            # multiple times in quick succession.  This leads to both requests
            # passing the uniqueness check and creating users (as the first one
            # hasn't committed when the second one runs the check).  We retain
            # the first one and delete the dupes.
            users = User.objects.filter(email=user.email)
            user = users[0]
            for u in users[1:]:
                u.delete()

        print("done registering")
        auth_login(self.request, user)

        return user

    def send_registration_email(self, user):
        code = self.communication_type_code
        try:
            muser = Seller.objects.filter(oscarUserID=user.id)[0]
        except:
            muser = None
        ctx = {'user': user,
               'muser': muser, 
               'site': get_current_site(self.request)}
        messages = CommunicationEventType.objects.get_and_render(
            code, ctx)
        if messages and messages['body']:
            Dispatcher().dispatch_user_messages(user, messages)


class AccountRegistrationView(RegisterUserMixin, FormView):
    form_class = EmailUserCreationForm
    template_name = 'customer/registration.html'
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return super(AccountRegistrationView, self).get(
            request, *args, **kwargs)

    def get_logged_in_redirect(self):
        return reverse('customer:summary')

    def get_form_kwargs(self):
        kwargs = super(AccountRegistrationView, self).get_form_kwargs()
        kwargs['initial'] = {
            'email': self.request.GET.get('email', ''),
            'redirect_url': self.request.GET.get(self.redirect_field_name, '')
        }
        kwargs['host'] = self.request.get_host()
        return kwargs

    def get_context_data(self, *args, **kwargs):
        ctx = super(AccountRegistrationView, self).get_context_data(
            *args, **kwargs)
        ctx['cancel_url'] = self.request.META.get('HTTP_REFERER', None)
        return ctx

    def form_valid(self, form):
        self.register_user(form)
        return HttpResponseRedirect(
            form.cleaned_data['redirect_url'])


class AccountAuthView(RegisterUserMixin, TemplateView):
    """
    This is actually a slightly odd double form view
    """
    template_name = 'customer/login_registration.html'
    login_prefix, registration_prefix = 'login', 'registration'
    login_form_class = EmailAuthenticationForm
    registration_form_class = EmailUserCreationForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated():
            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        return super(AccountAuthView, self).get(
            request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        ctx = super(AccountAuthView, self).get_context_data(*args, **kwargs)
        ctx.update(kwargs)

        # Don't pass request as we don't want to trigger validation of BOTH
        # forms.
        if 'login_form' not in kwargs:
            ctx['login_form'] = self.get_login_form()
        if 'registration_form' not in kwargs:
            ctx['registration_form'] = self.get_registration_form()
        return ctx

    def get_login_form(self, request=None):
        return self.login_form_class(**self.get_login_form_kwargs(request))

    def get_login_form_kwargs(self, request=None):
        kwargs = {}
        kwargs['host'] = self.request.get_host()
        kwargs['prefix'] = self.login_prefix
        kwargs['initial'] = {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }
        if request and request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': request.POST,
                'files': request.FILES,
            })
        return kwargs

    def get_registration_form(self, request=None):
        return self.registration_form_class(
            **self.get_registration_form_kwargs(request))

    def get_registration_form_kwargs(self, request=None):
        kwargs = {}
        kwargs['host'] = self.request.get_host()
        kwargs['prefix'] = self.registration_prefix
        kwargs['initial'] = {
            'redirect_url': self.request.GET.get(self.redirect_field_name, ''),
        }
        if request and request.method in ('POST', 'PUT'):
            kwargs.update({
                'data': request.POST,
                'files': request.FILES,
            })
        return kwargs

    def post(self, request, *args, **kwargs):
        # Use the name of the submit button to determine which form to validate
        if u'login_submit' in request.POST:
            return self.validate_login_form()
        elif u'registration_submit' in request.POST:
            return self.validate_registration_form()
        return self.get(request)

    def validate_login_form(self):
        form = self.get_login_form(self.request)
        if form.is_valid():
            auth_login(self.request, form.get_user())
            return HttpResponseRedirect(form.cleaned_data['redirect_url'])

        ctx = self.get_context_data(login_form=form)
        return self.render_to_response(ctx)

    def validate_registration_form(self):
        form = self.get_registration_form(self.request)
        if form.is_valid():
            self.register_user(form)
            return HttpResponseRedirect(form.cleaned_data['redirect_url'])

        ctx = self.get_context_data(registration_form=form)
        return self.render_to_response(ctx)


class EmailHistoryView(ListView):
    """Customer email history"""
    context_object_name = "emails"
    template_name = 'customer/email_list.html'
    paginate_by = 20

    def get_queryset(self):
        """Return a customer's emails """
        if self.request.GET.has_key('sent'):
            self.template_name='customer/sent_email_list.html'
            return Email._default_manager.filter(sender=self.request.user)
        else:
            return Email._default_manager.filter(user=self.request.user)


class EmailDetailView(DetailView):
    """Customer order details"""
    template_name = "customer/email.html"
    context_object_name = 'email'

    def get_object(self, queryset=None):
        """Return an order object or 404"""

        if self.request.GET.has_key('sent'):
            return get_object_or_404(Email, sender=self.request.user,
                                 id=self.kwargs['email_id'])
        else:
            return get_object_or_404(Email, user=self.request.user,
                                 id=self.kwargs['email_id'])


class OrderHistoryView(ListView):
    """
    Customer order history
    """
    context_object_name = "orders"
    template_header = "Order"
    template_name = 'customer/order_list.html'
    paginate_by = 20
    model = Order
    form_class = SearchByDateRangeForm

    def get(self, request, *args, **kwargs):
        if 'date_from' in request.GET:
            self.form = SearchByDateRangeForm(self.request.GET)
            if not self.form.is_valid():
                self.object_list = self.get_queryset()
                ctx = self.get_context_data(object_list=self.object_list)
                return self.render_to_response(ctx)
        else:
            self.form = SearchByDateRangeForm()
        return super(OrderHistoryView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        qs = self.model._default_manager.filter(user=self.request.user)
        if self.form.is_bound and self.form.is_valid():
            qs = qs.filter(**self.form.get_filters())
        return qs

    def get_context_data(self, *args, **kwargs):
        ctx = super(OrderHistoryView, self).get_context_data(*args, **kwargs)
        ctx['form'] = self.form
        ctx['order_or_sales_title'] = self.template_header
        return ctx


class SalesHistoryView(OrderHistoryView):
    """
    Customer sales history
    """
    #context_object_name = "orders"
    template_header = "Sales"
    template_name = 'customer/sales_list.html'
    #template_name = 'customer/order_list.html'

    def get_queryset(self):
        basketsForThisSeller = Basket.objects.filter(seller__user=self.request.user)
        basketIds = [b.id for b in basketsForThisSeller]
        ##sales = Order._default_manager.filter(basket_id__in=basketIds)

        qs = self.model._default_manager.filter(basket_id__in=basketIds)
        if self.form.is_bound and self.form.is_valid():
            qs = qs.filter(**self.form.get_filters())
        return qs


class OrderDetailView(PostActionMixin, DetailView):
    """Customer order details"""
    model = Order

    def get_template_names(self):
        return ["customer/order.html"]

    def get_object(self, queryset=None):

        if self.request.GET.has_key('user_id'):
            user = User.objects.filter(id=self.request.GET['user_id'])
        else:
            user = self.request.user

        

        o =  get_object_or_404(self.model, user=user,
                                 number=self.kwargs['order_number'])


        if user != self.request.user and not self.request.user.is_staff:
            ## don't show this order unless admin, buyer, or seller
            firstLine = OrderLine.objects.filter(order=o)[0]
            partner = firstLine.partner
            seller = partner.user
            if seller != self.request.user:
                self.response = HttpResponseRedirect(
                reverse('catalogue:index'))
                return

        return o


    def do_reorder(self, order):
        """
        'Re-order' a previous order.

        This puts the contents of the previous order into your basket
        """

        # Collect lines to be added to the basket and any warnings for lines
        # that are no longer available.
        firstLine in order.lines.all()[0]
        seller = firstLine.partner
        #basket = getBasket(seller)
        #try:
        #    basketForBooth = Basket.objects.filter
        lines_to_add = []
        warnings = []
        for line in order.lines.all():
            is_available, reason = line.is_available_to_reorder(basket,
                self.request.user)
            if is_available:
                lines_to_add.append(line)
            else:
                warnings.append(reason)

        # Check whether the number of items in the basket won't exceed the
        # maximum.
        total_quantity = sum([line.quantity for line in lines_to_add])
        is_quantity_allowed, reason = basket.is_quantity_allowed(
            total_quantity)
        if not is_quantity_allowed:
            messages.warning(self.request, reason)
            self.response = HttpResponseRedirect(
                reverse('customer:order-list'))
            return

        # Add any warnings
        for warning in warnings:
            messages.warning(self.request, warning)

        for line in lines_to_add:
            options = []
            for attribute in line.attributes.all():
                if attribute.option:
                    options.append({
                        'option': attribute.option,
                        'value': attribute.value})
            basket.add_product(line.product, line.quantity, options)

        if len(lines_to_add) > 0:
            self.response = HttpResponseRedirect(reverse('basket:summary'))
            messages.info(
                self.request,
                _("All available lines from order %(number)s "
                  "have been added to your basket") % {'number': order.number})
        else:
            self.response = HttpResponseRedirect(
                reverse('customer:order-list'))
            messages.warning(
                self.request,
                _("It is not possible to re-order order %(number)s "
                  "as none of its lines are available to purchase") %
                {'number': order.number})



class SaleDetailView(OrderDetailView, UpdateView):
    """Sale details"""

    parcel_formset = ParcelFormSet


    def get_template_names(self):
        return ["customer/sale.html"]

    def get_context_data(self, **kwargs):

        self.object = self.get_object()
        ctx = super(SaleDetailView, self).get_context_data(**kwargs)



        if 'parcel_formset' not in ctx:
            ctx['parcel_formset'] = self.parcel_formset(instance=self.object )#, minimum_forms=1, minimum_forms_message="At least one package    is needed for this order.")
            try:
                totalWeight = 0.0
                for line in self.object.lines.all():
                    firstLine = self.object.lines.all()[0]
                    weight = line.product.stockrecord.weight
                    quantity = line.quantity
                    totalWeight = totalWeight + weight*quantity
                if totalWeight > 0.0:
                    ctx['parcel_formset'].forms[0].fields['weight'].initial = totalWeight
            except:
                pass
        return ctx



    # def form_valid(self, form):
    #     #context = self.get_context_data()
    #     #bookimage_form = context['bookimage_formset']
    #     #bookpage_form = context['bookpage_formset']
    #     parcel_formset = ParcelFormSet(self.request.POST)
    #     self.object = form.save()
    #     parcel_formset.instance = self.object
    #     parcel_formset.save()
    #     messages.info(self.request,
    #                      _("Added a package "))
    #     return self.render_to_response()


    def post(self, request, *args, **kwargs):

        ## don't process formset if doing something else.......
        if self.request.POST.has_key('action'):
            return super(SaleDetailView, self).post(request, *args, **kwargs)

        parcel_formset = ParcelFormSet(self.request.POST, instance=self.get_object())


        #parcel_formset.clean()
        validVal = parcel_formset.is_valid()
        if validVal:
            parcel_formset.save()
            messages.success(self.request,
                        _("Added a package "))
            ctx = self.get_context_data()
        else:
            messages.error(self.request,
                        _("Please correct errors in the package specification "))
            ctx = self.get_context_data(parcel_formset=parcel_formset)
        #self.parcel_formset.save(instance=self.get_object())
        #ctx = self.get_context_data(
        #                             ##parcel_formset=parcel_formset,
        #                             ) #,

        ctx['parcelFormValid'] = validVal
        return self.render_to_response(ctx)

        


    # def form_valid(self, form):
    #     messages.info(self.request,
    #                     _("Added a package "))
    #     parcel_formset = self.parcel_formset(self.request.POST,
    #                                          instance=self.object)
    #     parcel_formset.save()
    #     ctx = self.get_context_data(
    #                                  parcel_formset=parcel_formset,
    #                                  ) #,

    #     return self.render_to_response()
    #     #
    
    #     return self.process_all_forms(form)

    # def form_invalid(self, form):
    #     return self.process_all_forms(form)

    # def process_all_forms(self, form):
    #     """
    #     Short-circuits the regular logic to have one place to have our
    #     logic to check all forms
    #     """
    #     # Need to create the parcel here because the inline forms need it
    #     # can't use commit=False because ParcelForm does not support it???


    #     #parcel_formset = self.parcel_formset(self.request.POST,
    #     #                                         instance=self.object)


    #     if self.parcel_formset.is_valid:
    #         self.parcel_formset.save()

    #         messages.info(self.request,
    #                    _("Added a package "))
    #         ctx = self.get_context_data(
    #                                 parcel_formset=parcel_formset,
    #                                 ) #,
    #         return self.render_to_response()

    #         #return HttpResponseRedirect(self.get_success_url())
    #     else:
    #         messages.error(self.request,
    #                    _("There is more information needed to create the item -- please "
    #                      "see below to add to or correct the form. "))
        
    #         ctx = self.get_context_data(

    #                                 parcel_formset=parcel_formset,
    #                                 ) #,
    #         return self.render_to_response(ctx)
    #         #return self.forms_valid(parcel_formset) 



    def do_show_label(self, order):
        """
        show shipping label for a previous order.

        """
        print "POSSST"
        print self.request.POST

        self.object = self.get_object()
        #try:
        basket = get_object_or_404(Basket, id = order.basket_id)

        shipping_info = basket.shipping_info

        if shipping_info:
            shipDict = json.loads(shipping_info)
            easypost.api_key = settings.EASYPOST_KEY
            eo =  easypost.convert_to_easypost_object(shipDict['easypost_info'], easypost.api_key)

            selectedRate = None
            if self.object.parcels.count():
                ## if UPS, recalculate the parcel based on new info
                for parcel in self.object.parcels.all():

                    if not parcel.shipping_info_json:
                        parcelEP = easypost.Parcel.create(
                            length = parcel.length, 
                            width = parcel.width,
                            height = parcel.height,
                            weight = parcel.weight,
                        )

                        pshi = easypost.Shipment.create(
                            to_address = eo.to_address,
                            from_address = eo.from_address,
                            parcel = parcelEP,

                        )
                        shipDict = {}
                        shipDict['easypost_info'] = pshi.to_dict()
                        parcel.shipping_info_json = json.dumps(shipDict)
                        parcel.save()

                    else:
                        shipDict = json.loads(parcel.shipping_info_json)
                        easypost.api_key = settings.EASYPOST_KEY
                        pshi =  easypost.convert_to_easypost_object(shipDict['easypost_info'], easypost.api_key)

                    if not pshi.postage_label:
                        for r in pshi.rates:
                            if r.carrier == order.shipping_carrier and r.service == order.shipping_service:
                                selectedRate = r
                        labelInfo = pshi.buy(rate=selectedRate)
                        shipDict = {}
                        shipDict['easypost_info'] = pshi.to_dict()
                        parcel.shipping_info_json = json.dumps(shipDict)
                        parcel.save()
                        parcel.shipping_label_json = labelInfo  

                    postage_label = pshi.postage_label

            else:
                ## get the rate from what is saved in the basket.
                for r in eo.rates:
                    if r.carrier == order.shipping_carrier and r.service == order.shipping_service:
                        selectedRate = r

                print eo
                eo.refresh()
                if not eo.postage_label:
                    labelInfo = eo.buy(rate=selectedRate)
                    order.shipping_label_json = labelInfo  
                    postage_label = eo.postage_label
                else:
                    postage_label = eo.postage_label
                
            #print self.request.POST
            ## can switch to show PDF, get hidden POST data
            self.response = HttpResponseRedirect(postage_label.label_url) 
            ##self.response = HttpResponseRedirect(eo.postage_label.label_pdf_url) 
            return

        #except:
        self.response = HttpResponseRedirect(reverse('customer:sales-list'))
        messages.warning(
                self.request,
                _("It is not possible to get a label for order %(number)s "
                  "as the service is unavailable, please contact support") %
                {'number': order.number})


class OrderLineView(PostActionMixin, DetailView):
    """Customer order line"""

    def get_object(self, queryset=None):
        """Return an order object or 404"""
        order = get_object_or_404(Order, user=self.request.user,
                                  number=self.kwargs['order_number'])
        return order.lines.get(id=self.kwargs['line_id'])

    def do_reorder(self, line):
        self.response = HttpResponseRedirect(reverse('customer:order',
                                    args=(int(self.kwargs['order_number']),)))
        basket = self.request.basket

        line_available_to_reorder, reason = line.is_available_to_reorder(basket,
            self.request.user)

        if not line_available_to_reorder:
            messages.warning(self.request, reason)
            return

        # We need to pass response to the get_or_create... method
        # as a new basket might need to be created
        self.response = HttpResponseRedirect(reverse('basket:summary'))

        # Convert line attributes into basket options
        options = []
        for attribute in line.attributes.all():
            if attribute.option:
                options.append({'option': attribute.option, 'value': attribute.value})
        basket.add_product(line.product, line.quantity, options)

        if line.quantity > 1:
            msg = _("%(qty)d copies of '%(product)s' have been added to your basket") % {
                'qty': line.quantity, 'product': line.product}
        else:
            msg = _("'%s' has been added to your basket") % line.product

        messages.info(self.request, msg)


# ------------
# Address book
# ------------


class AddressListView(ListView):
    """Customer address book"""
    context_object_name = "addresses"
    template_name = 'customer/address_list.html'
    paginate_by = 40

    def get_queryset(self):
        """Return a customer's addresses"""
        return UserAddress._default_manager.filter(user=self.request.user)


class AddressCreateView(CreateView):
    form_class = UserAddressForm
    mode = UserAddress
    template_name = 'customer/address_form.html'

    def get_form_kwargs(self):
        kwargs = super(AddressCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(AddressCreateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Add a new address')
        return ctx

    def get_success_url(self):
        messages.success(self.request, _("Address saved"))
        return reverse('customer:address-list')


class AddressUpdateView(UpdateView):
    form_class = UserAddressForm
    model = UserAddress
    template_name = 'customer/address_form.html'

    def get_form_kwargs(self):
        kwargs = super(AddressUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(AddressUpdateView, self).get_context_data(**kwargs)
        ctx['title'] = _('Edit address')
        return ctx

    def get_queryset(self):
        return self.request.user.addresses.all()

    def get_success_url(self):
        messages.success(self.request, _("Address saved"))
        return reverse('customer:address-list')


class AddressDeleteView(DeleteView):
    model = UserAddress
    template_name = "customer/address_delete.html"

    def get_queryset(self):
        return UserAddress._default_manager.filter(user=self.request.user)

    def get_success_url(self):
        return reverse('customer:address-list')


# ================
# SHIPPING ADDRESS
# ================


class StoreShippingAddressView(CreateView):
    """
    Determine the outgoing shipping address for the seller.

    The default behaviour is to display a list of addresses from the users's
    address book, from which the user can choose one to be their default outgoing shipping address.
    They can add/edit/delete these USER addresses. 

    Alternatively, the user can enter a USER address directly which will be
    saved as the default outgoing shipping address.
    """
    template_name = 'customer/store_address.html'
    form_class = UserAddressForm
    model = UserAddress

    #def __init__(self):
    #   super(StoreShippingAddressView, self).__init__(no_checkboxes=True)
    #   return

    def get(self, request, *args, **kwargs):

        return super(StoreShippingAddressView, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = {}
        initial['is_default_for_store']=True

        return initial

    #def get_initial(self):
    #    return self.checkout_session.new_shipping_address_fields()

    # def get_form(self, form_class):
    #     # Initialize the form with initial values and the subscriber object
    #     # to be used in EmailPreferenceForm for populating fields

    #     return form_class(
    #         initial=self.get_initial(),
    #         #subscriber=self.subscriber,
    #         no_checkboxes = True
    #     )


    def get_form_kwargs(self):
        kwargs = super(StoreShippingAddressView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['no_checkboxes'] = True

        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super(StoreShippingAddressView, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            # Look up address book data
            kwargs['addresses'] = self.get_available_addresses()

        try:
            partner = self.request.user.partner
            partnerAddress = UserAddress._default_manager.filter(user=self.request.user).order_by('-is_default_for_shipping')[0]
            kwargs['partnerAddress'] = partnerAddress
        except:
            kwargs['partnerAddress'] = None

        return kwargs

    def get_available_addresses(self):
        return UserAddress._default_manager.filter(user=self.request.user).order_by('-is_default_for_store')

    def post(self, request, *args, **kwargs):
        # Check if a store address was selected directly (eg no form was
        # filled in)
        ## invalid POST if not store...

        try:
            p = self.request.user.partner
        except:
            return HttpResponseRedirect(reverse('customer:address-list'))

        if self.request.user.is_authenticated() and 'address_id' in self.request.POST:
            address = UserAddress._default_manager.get(
                pk=self.request.POST['address_id'], user=self.request.user)
            action = self.request.POST.get('action', None)
            if action == 'ship_to':
                # User has selected a previous address to ship to

                qq = UserAddress._default_manager.filter(user=self.request.user, is_default_for_store=True)
                for q in qq:
                    q.is_default_for_store = False
                    q.save()
                address.is_default_for_store = True
                address.save()
                return HttpResponseRedirect(self.get_success_url())
            elif action == 'delete':
                # Delete the selected address
                address.delete()
                messages.info(self.request, _("Address deleted from your address book"))
                return HttpResponseRedirect(reverse('customer:address-list'))
            else:
                return HttpResponseBadRequest()
        else:

            return super(StoreShippingAddressView, self).post(
                request, *args, **kwargs)

    def form_valid(self, form):
        # Store the address details in the session and redirect to next step
        #address_fields = dict(
        #    (k, v) for (k, v) in form.instance.__dict__.items()
        #    if not k.startswith('_'))
        #self.checkout_session.ship_to_new_address(address_fields)
        ## set as default shipping address, since that's what this is all about

        #form.cleaned_data['is_default_for_store'] = True
        form.instance.is_default_for_store = True
        return super(StoreShippingAddressView, self).form_valid(form)

    def get_success_url(self):

        messages.success(self.request, _("Outgoing Shipping Address saved"))
        return "../../catalogue?booth=" + str(self.request.user.partner.id)




class StoreShippingOptionsView(TemplateView):
    """
    Determine the outgoing shipping preferences for the seller.

    """
    template_name = 'customer/store_ship_options.html'
    #form_class = UserAddressForm
    #model = UserAddress

    #def __init__(self):
    #   super(StoreShippingAddressView, self).__init__(no_checkboxes=True)
    #   return

##    def get(self, request, *args, **kwargs):

##        return super(StoreShippingOptionsView, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = {}
        initial['is_default_for_store']=True

        return initial

    def get_context_data(self, **kwargs):
        ctx = super(StoreShippingOptionsView, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            ## get current shipping preferences
            partner = self.request.user.partner
            if partner.shipping_options:
                soptsDict = json.loads(partner.shipping_options)
                if soptsDict:
                    ctx['self_ship'] = soptsDict.get('self_ship')
                    ctx['calculate_ship'] = soptsDict.get('calculate_ship')

                    ctx['printLabel'] = soptsDict.get('printLabel')

                    ctx['PMSmall_used'] = soptsDict.get('PMSmall_used')
                    ctx['PMMedium_used'] = soptsDict.get('PMMedium_used')
                    ctx['PMLarge_used'] = soptsDict.get('PMLarge_used')

                    ctx['first_used'] = soptsDict.get('first_used')
                    ctx['UPS_used'] = soptsDict.get('UPS_used')

                    ctx['local_pickup_used'] = soptsDict.get('local_pickup_used')
                    ctx['local_delivery_used'] = soptsDict.get('local_delivery_used')
                    ctx['local_delivery_cost'] = soptsDict.get('local_delivery_cost')
                    ctx['local_delivery_radius'] = soptsDict.get('local_delivery_radius')

        return ctx

    def post(self, request, *args, **kwargs):
        # Check if ship preferences 

        try:
            partner = self.request.user.partner
        except:
            return HttpResponseRedirect(reverse('catalogue:index'))

        if self.request.user.is_authenticated():

                ## action = self.request.POST.get('action', None)

            #if partner.shipping_options:
            #    soptsDict = json.loads(partner.shipping_options)
            #else:
            #    ## 
            soptsDict = {}


            ## process form
            data = self.request.POST

            ## add shipping options to the stockrecord
            shipChoice = data.get('shipChoice')
            soptsDict['shipChoice'] = data.get("shipChoice")

            ## check if shipping at all
            if data.get("remote_ship_toggle") == "on":
                if shipChoice == "calculate_ship":
                    soptsDict['calculate_ship'] = True
                    soptsDict['self_ship'] = False
                    if data.get('print_label_toggle') == "on":
                        soptsDict['printLabel'] = True

                if shipChoice == "self_ship":
                    soptsDict['calculate_ship'] = False
                    soptsDict['self_ship'] = True 
            else:
                ## not shipping
                soptsDict['calculate_ship'] = False
                soptsDict['self_ship'] = False


            ## priority mail
            if data.get("PM_toggle") == "on":
                if data.get("PMSmall_toggle") == "on":
                    soptsDict['PMSmall_used'] = True           

                if data.get("PMMedium_toggle") == "on":
                    soptsDict['PMMedium_used'] = True           

                if data.get("PMLarge_toggle") == "on":
                    soptsDict['PMLarge_used'] = True           

            if data.get("FirstClass_toggle") == "on":
                soptsDict['first_used'] = True  

            if data.get("UPS_toggle") == "on":
                soptsDict['UPS_used'] = True  

            if data.get("local_pickup_toggle") == "on":
                soptsDict['local_pickup_used'] = True  

            if data.get("local_delivery_toggle") == "on":
                soptsDict['local_delivery_used'] = True 
            
            soptsDict['local_delivery_cost'] = data.get('local_delivery_cost')
            soptsDict['local_delivery_radius'] = data.get('local_delivery_radius')                 


            ## repack
            partner.shipping_options = json.dumps(soptsDict)

            #if soptsDict.get('first_used') or soptsDict.get('UPS_used'):
            #    stockrecord.is_shippable = True
            if data.get('remote_ship_toggle') != "on":
                soptsDict['calculate_ship'] = False
                soptsDict['self_ship'] = False
                

            partner.save()

            messages.success(self.request, _("Your shipping preferences have been saved"))


            ## if the seller does not have a shipping address, send them to that page.
            ## get primary partner address
            try:
                shipFromAddress = UserAddress._default_manager.filter(user=partner.user).order_by('-is_default_for_store')[0]
            except:
                shipFromAddress = None

            if soptsDict.get('printLabel') == True and not shipFromAddress:
                return HttpResponseRedirect(reverse('customer:store-shipping-address'))

            ## otherwise go back to the booth 
            return HttpResponseRedirect(self.get_success_url())




        #         # Delete the selected address

        #         messages.info(self.request, _("Address deleted from your address book"))
        #         return HttpResponseRedirect(reverse('customer:address-list'))
        #     else:
        #         return HttpResponseBadRequest()
        # else:
        #     return HttpResponseRedirect(reverse('catalogue:index'))



    def get_success_url(self):

        #messages.success(self.request, _("Shipping preferences saved"))
        return "../../catalogue?booth=" + str(self.request.user.partner.id)




class StorePickupLocationView(CreateView):
    """
    Get a pickup location and time (optional) for the seller.

    The default behaviour is to display a list of addresses from the users's
    address book, from which the user can choose one to be a pickup location.
    They can add/edit/delete these USER addresses. 

    Alternatively, the user can enter a USER address directly which will be
    saved as a pickup location.
    """
    template_name = 'customer/pickup_location.html'
    form_class = UserAddressForm
    model = UserAddress

    #def __init__(self):
    #   super(StoreShippingAddressView, self).__init__(no_checkboxes=True)
    #   return

    def get(self, request, *args, **kwargs):

        return super(StorePickupLocationView, self).get(request, *args, **kwargs)

    def get_initial(self):
        initial = {}
        initial['is_default_for_store']=True

        return initial

    #def get_initial(self):
    #    return self.checkout_session.new_shipping_address_fields()

    # def get_form(self, form_class):
    #     # Initialize the form with initial values and the subscriber object
    #     # to be used in EmailPreferenceForm for populating fields

    #     return form_class(
    #         initial=self.get_initial(),
    #         #subscriber=self.subscriber,
    #         no_checkboxes = True
    #     )


    def get_form_kwargs(self):
        kwargs = super(StorePickupLocationView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['no_checkboxes'] = True

        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super(StorePickupLocationView, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated():
            # Look up address book data
            kwargs['addresses'] = self.get_available_addresses()

        try:
            partner = self.request.user.partner
            partnerAddress = UserAddress._default_manager.filter(user=self.request.user).order_by('-is_default_for_shipping')[0]
            kwargs['partnerAddress'] = partnerAddress
        except:
            kwargs['partnerAddress'] = None

        return kwargs

    def get_available_addresses(self):
        return UserAddress._default_manager.filter(user=self.request.user).order_by('-is_default_for_store')

    def post(self, request, *args, **kwargs):
        # Check if a store address was selected directly (eg no form was
        # filled in)
        ## invalid POST if not store...

        try:
            p = self.request.user.partner
        except:
            return HttpResponseRedirect(reverse('customer:address-list'))

        if self.request.user.is_authenticated() and 'address_id' in self.request.POST:
            address = UserAddress._default_manager.get(
                pk=self.request.POST['address_id'], user=self.request.user)
            action = self.request.POST.get('action', None)
            if action == 'ship_to':
                # User has selected a previous address to ship to

                #qq = UserAddress._default_manager.filter(user=self.request.user, is_default_for_store=True)
                #for q in qq:
                #    q.is_default_for_store = False
                #    q.save()
                #address.is_default_for_store = True
                
                address.save()
                
                return HttpResponseRedirect(self.get_success_url())
            elif action == 'delete':
                # Delete the selected address
                address.delete()
                messages.info(self.request, _("Address deleted from your address book"))
                return HttpResponseRedirect(reverse('customer:address-list'))
            else:
                return HttpResponseBadRequest()
        else:

            return super(StorePickupLocationView, self).post(
                request, *args, **kwargs)

    def form_valid(self, form):
        # Store the address details in the session and redirect to next step
        #address_fields = dict(
        #    (k, v) for (k, v) in form.instance.__dict__.items()
        #    if not k.startswith('_'))
        #self.checkout_session.ship_to_new_address(address_fields)
        ## set as default shipping address, since that's what this is all about

        #form.cleaned_data['is_default_for_store'] = True
        #form.instance.is_default_for_store = True
        return super(StorePickupLocationView, self).form_valid(form)

    def get_success_url(self):

        messages.success(self.request, _("Pickup location saved"))
        return "../../catalogue?booth=" + str(self.request.user.partner.id)





# ------------
# Order status
# ------------


class AnonymousOrderDetailView(DetailView):
    model = Order
    template_name = "customer/anon_order.html"

    def get_object(self, queryset=None):
        # Check URL hash matches that for order to prevent spoof attacks
        order = get_object_or_404(self.model, user=None,
                                  number=self.kwargs['order_number'])
        if self.kwargs['hash'] != order.verification_hash():
            raise Http404()
        return order


class ChangePasswordView(FormView):
    form_class = PasswordChangeForm
    template_name = 'customer/change_password_form.html'
    communication_type_code = 'PASSWORD_CHANGED'

    def get_form_kwargs(self):
        kwargs = super(ChangePasswordView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Password updated"))

        ctx = {
            'user': self.request.user,
            'site': get_current_site(self.request),
            'reset_url': get_password_reset_url(self.request.user),
        }
        msgs = CommunicationEventType.objects.get_and_render(
            code=self.communication_type_code, context=ctx)
        Dispatcher().dispatch_user_messages(self.request.user, msgs)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('customer:summary')



