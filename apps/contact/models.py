from collections import OrderedDict

from django.contrib.auth import get_user_model
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_enumfield import enum

from apps.contrib.models import MetaInformationArchiveAbstractModel

User = get_user_model()


class Contact(MetaInformationArchiveAbstractModel, models.Model):
    class DESIGNATION(enum.Enum):
        MR = 0
        MS = 1
        MRS = 2

        __labels__ = {
            MR: _("Mr"),
            MS: _("Ms"),
            MRS: _("Mrs"),
        }

    class GENDER(enum.Enum):
        MALE = 0
        FEMALE = 1
        OTHER = 2

        __labels__ = {
            MALE: _("Male"),
            FEMALE: _("Female"),
            OTHER: _("Other"),
        }

    designation = enum.EnumField(DESIGNATION)
    first_name = models.CharField(verbose_name=_('First Name'), max_length=256)
    last_name = models.CharField(verbose_name=_('Last Name'), max_length=256)
    full_name = models.CharField(verbose_name=_('Full Name'), max_length=512,
                                 blank=True, null=True,
                                 help_text=_('Auto generated'))
    gender = enum.EnumField(GENDER, verbose_name=_('Gender'))
    job_title = models.CharField(verbose_name=_('Job Title'), max_length=256)
    organization = models.ForeignKey('organization.Organization', verbose_name=_('Organization'),
                                     blank=True, null=True,
                                     related_name='contacts', on_delete=models.CASCADE)
    countries_of_operation = models.ManyToManyField('country.Country',
                                                    verbose_name=_('Countries of Operation'),
                                                    blank=True,
                                                    related_name='operating_contacts',
                                                    help_text=_(
                                                        'In which countries does this contact person'
                                                        ' operate?'
                                                    ))
    country = models.ForeignKey('country.Country',
                                verbose_name=_('Country'),
                                blank=True, null=True,
                                related_name='contacts', on_delete=models.SET_NULL)
    email = models.EmailField(verbose_name=_('Email'), blank=True, null=True)
    skype = models.CharField(verbose_name=_('Skype'), max_length=32,
                             blank=True, null=True)
    phone = models.CharField(verbose_name=_('Phone'), max_length=256,
                             blank=True, null=True)
    comment = models.TextField(verbose_name=_('Comment'), blank=True, null=True)

    def __str__(self):
        return f'{self.designation.name} {self.first_name} {self.last_name}'

    def get_full_name(self):
        return ' '.join([
            name for name in [self.first_name, self.last_name] if name
        ]) or self.email

    @classmethod
    def get_excel_sheets_data(cls, user_id, filters):
        from apps.contact.filters import ContactFilter

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        headers = OrderedDict(
            id='Id',
            designation='Designation',
            full_name='Name',
            gender='Gender',
            job_title='Job Title',
            country='Country',
            organization__name='Organization',
            operating_countries='Operating Countries',
            created_at='Created At',
            created_by='Created By',
            communications_count='Communications'
        )
        data = ContactFilter(
            data=filters,
            request=DummyRequest(user=User.objects.get(id=user_id)),
        ).qs.annotate(
            operating_countries=ArrayAgg('countries_of_operation__iso3'),
            communications_count=models.Count('communications', distinct=True),
        ).order_by('-created_at').select_related(
            'organization'
        ).prefetch_related(
            'countries_of_operation__iso3'
        )

        def transformer(datum):
            return {
                **datum,
                **dict(
                    designation=getattr(Contact.DESIGNATION.get(datum['designation']), 'name', ''),
                    gender=getattr(Contact.GENDER.get(datum['gender']), 'name', ''),
                )
            }

        return {
            'headers': headers,
            'data': data.values(*[header for header in headers.keys()]),
            'formulae': None,
            'transformer': transformer,
        }

    def save(self, *args, **kwargs):
        self.full_name = self.get_full_name()
        return super().save(*args, **kwargs)


class CommunicationMedium(models.Model):
    name = models.CharField(verbose_name=_('Name'), max_length=256)

    def __str__(self):
        return f'{self.name}'


class Communication(MetaInformationArchiveAbstractModel, models.Model):
    class COMMUNICATION_MEDIUM(enum.Enum):
        # keeping for the sake of migrations, remove it when recreating all migrations
        pass

    contact = models.ForeignKey('Contact', verbose_name=_('Contact'),
                                related_name='communications', on_delete=models.CASCADE)
    country = models.ForeignKey('country.Country', verbose_name=_('Country'),
                                blank=True, null=True,
                                related_name='communications', on_delete=models.CASCADE)
    subject = models.CharField(verbose_name=_('Subject'), max_length=512)
    content = models.TextField(verbose_name=_('Content'))
    date = models.DateField(verbose_name=_('Conducted Date'),
                            null=True, blank=True,
                            help_text=_('Date on which communication occurred.'))
    medium = models.ForeignKey(CommunicationMedium,
                               null=True, blank=False,
                               related_name='+', on_delete=models.SET_NULL)
    attachment = models.ForeignKey('contrib.Attachment', verbose_name='Attachment',
                                   on_delete=models.CASCADE, related_name='+',
                                   null=True, blank=True)

    def __str__(self):
        return f'{self.contact} {self.date}'
