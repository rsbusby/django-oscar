import logging

from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import get_model
from django.utils.http import int_to_base36
from django.contrib.auth.tokens import default_token_generator

CommunicationEvent = get_model('order', 'CommunicationEvent')
Email = get_model('customer', 'Email')


class Dispatcher(object):
    def __init__(self, logger=None):
        if not logger:
            logger = logging.getLogger(__name__)
        self.logger = logger

    # Public API methods

    def dispatch_direct_messages(self, recipient, messages):
        """
        Dispatch one-off messages to explicitly specified recipient(s).
        Without keeping a record. Not used as of Nov 2013
        """
        if messages['subject'] and messages['body']:
            self.send_email_messages(recipient, messages)

    def dispatch_order_messages(self, order, messages, event_type=None,
                                **kwargs):
        """
        Dispatch order-related messages to the customer
        """
        if order.is_anonymous:
            if 'email_address' in kwargs:
                self.send_email_messages(kwargs['email_address'], messages)
            elif order.guest_email:
                self.send_email_messages(order.guest_email, messages)
            else:
                return
        else:
            self.dispatch_user_messages(order.user, messages, None)

        # Create order comms event for audit
        if event_type:
            CommunicationEvent._default_manager.create(order=order,
                                                       event_type=event_type)

    def dispatch_user_messages(self, user, messages, sender=None, replyToFlag=False):
        """
        Send messages to a site user
        """

        if messages['subject'] and (messages['body'] or messages['html']):
            self.send_user_email_messages(user, messages, sender, replyToFlag)
        if messages['sms']:
            self.send_text_message(user, messages['sms'])


    def dispatch_guest_messages(self, guest_email, messages, sender=None,replyToFlag=False):
        """
        Send messages to an email address, keep a record in sender's database
        """    
        if messages['subject'] and (messages['body'] or messages['html']):
            self.send_guest_email_messages(guest_email, messages, sender, replyToFlag)

    # Internal

    def send_guest_email_messages(self, guest_email, messages, sender, replyToFlag):
        """
        Sends message to the guest's email and collects data in database
        """
        if not guest_email:
            self.logger.warning("Unable to send email messages as email address is not valid")
            return


        #create headers
        ## allow replies-


        replyTo = None
        if replyToFlag:
            replyTo = guest_email
        # if user.is_staff:
        #     ## set reply-to ?? 
        #     try:
        #         replyTo = sender.email
        #     except:
        #         pass

        email = self.send_email_messages(guest_email, messages, replyTo = replyTo)

        # Is user is signed in, record the event for audit
        
        if email and sender.is_authenticated():
            Email._default_manager.create(user=sender,
                                          sender=sender,
                                          subject=email.subject,
                                          body_text=email.body,
                                          body_html=messages['html'])




    def send_user_email_messages(self, user,  messages, sender, replyToFlag):
        """
        Sends message to the registered user / customer and collects data in database
        """

        if not user.email:
            self.logger.warning("Unable to send email messages as user #%d has no email address", user.id)
            return

        #create headers
        ## allow replies-
        replyTo = None
        if user.is_staff or replyToFlag:
            ## set reply-to ?? 
            try:
                replyTo = sender.email
            except:
                pass

        email = self.send_email_messages(user.email, messages, replyTo = replyTo)

        # Is user is signed in, record the event for audit
        if email and user.is_authenticated():
            Email._default_manager.create(user=user,
                                          sender=sender,
                                          subject=email.subject,
                                          body_text=email.body,
                                          body_html=messages['html'])

    def send_email_messages(self, recipient, messages, replyTo=None):
        """
        Plain email sending to the specified recipient
        """
        if hasattr(settings, 'OSCAR_FROM_EMAIL'):
            from_email = settings.OSCAR_FROM_EMAIL
        else:
            from_email = None

        if replyTo:
            headers = {'Reply-To': replyTo}
        else:
            headers = None


        # Determine whether we are sending a HTML version too
        if messages['html']:
            email = EmailMultiAlternatives(messages['subject'],
                                           messages['body'],
                                           from_email=from_email,
                                           to=[recipient],
                                           headers=headers)
            email.attach_alternative(messages['html'], "text/html")
        else:
            email = EmailMessage(messages['subject'],
                                 messages['body'],
                                 from_email=from_email,
                                 to=[recipient], 
                                 headers = headers)
        self.logger.info("Sending email to %s" % recipient)
        email.send()

        return email




    def send_text_message(self, user, event_type):
        raise NotImplementedError


    def send_email_messages_with_images(self, recipient, messages):
        """
        Plain email sending to the specified recipient
        """
        if hasattr(settings, 'OSCAR_FROM_EMAIL'):
            from_email = settings.OSCAR_FROM_EMAIL
        else:
            from_email = None

        ## prepare image
        f = open(filename, "rb") 
        image_data = f.read()  # Read from a png file
        image_cid = make_msgid("img")  # Content ID per RFC 2045 section 7 (with <...>)
        image_cid_no_brackets = image_cid[1:-1]  # Without <...>, for use as the <img> tag src

        text_content = 'This has an inline image.'
        html_content = '<p>This has an <img src="cid:%s" alt="inline" /> image.</p>' % image_cid_no_brackets


        # Determine whether we are sending a HTML version too
        if messages['html']:
            email = EmailMultiAlternatives(messages['subject'],
                                           messages['body'],
                                           from_email=from_email,
                                           to=[recipient])
            email.attach_alternative(messages['html'], "text/html")
        else:
            email = EmailMessage(messages['subject'],
                                 messages['body'],
                                 from_email=from_email,
                                 to=[recipient])
        self.logger.info("Sending email to %s" % recipient)
        #email.send()

       
        email = mail.EmailMultiAlternatives('Subject', text_content, 'from@example.com', ['to@example.com'])
        email.attach_alternative(html_content, "text/html")

        image = MIMEImage(image_data)
        image.add_header('Content-ID', image_cid)
        email.attach(image)
        email.send()

        return email


def get_password_reset_url(user, token_generator=default_token_generator):
    """
    Generate a password-reset URL for a given user
    """
    return reverse('password-reset-confirm', kwargs={
        'uidb36': int_to_base36(user.id),
        'token': default_token_generator.make_token(user)})


def normalise_email(email):
    """
    The local part of an email address is case-sensitive, the domain part isn't.
    This function lowercases the host and should be used in all email handling.
    """
    clean_email = email.strip()
    if '@' in clean_email:
        local, host = clean_email.split('@')
        return local + '@' + host.lower()
    return clean_email
