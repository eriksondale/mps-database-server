from django import forms
from captcha.fields import CaptchaField
from registration.forms import RegistrationFormUniqueEmail
from django.contrib.auth.forms import PasswordResetForm, UserChangeForm
from django.contrib.auth.models import User
from mps.settings import DEFAULT_FROM_EMAIL

from django.template.loader import render_to_string


class SignOffMixin(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(SignOffMixin, self).__init__(*args, **kwargs)

        instance = kwargs.get('instance', None)

        if instance and instance.signed_off_by:
            self.fields['signed_off'].initial = True

    signed_off = forms.BooleanField(required=False)


class SearchForm(forms.Form):
    """Form for Global/Bioactivity searches"""
    app = forms.CharField(max_length=50)
    compound = forms.CharField(max_length=100, required=False)
    target = forms.CharField(max_length=100, required=False)
    name = forms.CharField(max_length=100, required=False)
    pubchem = forms.BooleanField(required=False)
    exclude_targetless = forms.BooleanField(required=False)
    exclude_organismless = forms.BooleanField(required=False)
    search_term = forms.CharField(max_length=500, required=False)

    def clean(self):
        super(SearchForm, self).clean()

        app = self.cleaned_data.get('app', '')
        compound = self.cleaned_data.get('compound', '')
        target = self.cleaned_data.get('target', '')
        name = self.cleaned_data.get('name', '')

        if app == "Bioactivities" and not any([compound, target, name]):
            raise forms.ValidationError(
                'You must have at least one search term'
            )

        return self.cleaned_data


# Add captcha to registration form
class CaptchaRegistrationForm(RegistrationFormUniqueEmail):
    """Extended Registration Form with Captcha"""
    captcha = CaptchaField()
    first_name = forms.CharField(initial='')
    last_name = forms.CharField(initial='')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()[:30].strip()

        return username

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()[:30]

        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()[:30]

        return last_name

    def save(self, commit=True):
        new_user = super(CaptchaRegistrationForm, self).save()
        new_user.first_name = self.cleaned_data.get('first_name')
        new_user.last_name = self.cleaned_data.get('last_name')
        new_user.save()

        # Magic strings are in poor taste, should use a template instead
        subject = 'New User: {0} {1}'.format(new_user.first_name, new_user.last_name)
        message = render_to_string(
            'registration/superuser_new_user_alert.txt',
            {
                'user': new_user
            }
        )

        users_to_be_alerted = User.objects.filter(is_superuser=True, is_active=True)

        for user_to_be_alerted in users_to_be_alerted:
            user_to_be_alerted.email_user(subject, message, DEFAULT_FROM_EMAIL)

        return new_user


# Add captcha to reset form
class CaptchaResetForm(PasswordResetForm):
    """Extended Password Reset form with Captcha"""
    captcha = CaptchaField()

    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError("There is no user registered with the specified email address!")

        return email


class MyUserChangeForm(UserChangeForm):
    # Very sloppy use of inheritance
    class Meta(UserChangeForm.Meta):
        help_texts = {
            'groups':   '***Assign permissions as follows:***<br>'
                        'data group viewer: {{ data group }} Viewer<br>'
                        'data group editor: {{ data group }}<br>'
                        'data group admin (can sign off): {{ data group }} Admin<br>'
                        'stakeholder group admin (can approve): {{ access group }} Admin<br>'
                        'stakeholder/access group viewer: {{ access group }} Viewer<br><br>'
                        '***NOTE THAT EDITORS ARE ALSO VIEWERS AND ADMINS ARE EDITORS AND VIEWERS***<br><br>',
            'user_permissions': '***THIS IS FOR THE ADMIN INTERFACE ONLY***<br>',
        }
