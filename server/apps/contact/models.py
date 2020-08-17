from enum import Enum

from django.db import models


class Contact(models.Model):
    class DESIGNATION(Enum):
        MR = 0
        MS = 1

        @classmethod
        def choices(cls):
            return tuple((i.value, i.name) for i in cls)

    class GENDER(Enum):
        Male = 0
        Female = 1
        Other = 2

        @classmethod
        def choices(cls):
            return tuple((i.value, i.name) for i in cls)

    designation = models.PositiveSmallIntegerField('Designation', choices=DESIGNATION.choices())
    first_name = models.CharField('First Name', max_length=256)
    last_name = models.CharField('Last Name', max_length=256)
    gender = models.PositiveSmallIntegerField('Gender', choices=GENDER.choices())
    job_title = models.CharField('Job Title', max_length=256)
    organization = models.ForeignKey('organization.Organization',
                                     related_name='contacts', on_delete=models.CASCADE)
    countries_of_operation = models.ManyToManyField('country.Country',
                                                    blank=True, null=True,
                                                    related_name='operating_contacts',
                                                    help_text='In which countries does this contact person'
                                                              ' operate?')
    country = models.ForeignKey('country.Country',
                                blank=True, null=True,
                                related_name='contacts', on_delete=models.SET_NULL)
    email = models.EmailField('Email', blank=True, null=True)
    phone = models.CharField('Phone', max_length=32, blank=True, null=True)
    comment = models.TextField('Comment', blank=True, null=True)

    def __str__(self):
        return f'{self.get_designation_display()} {self.first_name} {self.last_name}'


class Communication(models.Model):
    class COMMUNICATION_MEDIUM(Enum):
        MAIL = 0
        PHONE = 1

        @classmethod
        def choices(cls):
            return tuple((i.value, i.name) for i in cls)

    contact = models.ForeignKey('Contact',
                                related_name='communications', on_delete=models.CASCADE)
    title = models.CharField('Title', max_length=256,
                             blank=True, null=True)
    subject = models.CharField('Subject', max_length=512)
    content = models.TextField('Content')
    date_time = models.DateTimeField('Date',
                                     null=True, blank=True,
                                     help_text='Date on which communication occurred.')
    medium = models.PositiveSmallIntegerField('Medium', choices=COMMUNICATION_MEDIUM.choices())
    # todo attachment

    def __str__(self):
        return f'{self.contact} {self.date_time}'
