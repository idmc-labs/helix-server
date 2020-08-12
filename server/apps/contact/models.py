from django.db import models


class Contact(models.Model):
    MR = 0
    MS = 1
    DESIGNATION_CHOICES = (
        (MR, 'Mr'),
        (MS, 'Ms'),
    )

    designation = models.PositiveSmallIntegerField('Designation', choices=DESIGNATION_CHOICES)
    name = models.CharField('Name', max_length=256)
    # todo country model
    country = models.PositiveIntegerField('Country', default=1)
    organization = models.ForeignKey('organization.Organization',
                                     related_name='contacts', on_delete=models.CASCADE)
    job_title = models.CharField('Job Title', max_length=256)

    def __str__(self):
        return f'{self.designation} {self.name}'


class Communication(models.Model):
    MAIL = 0
    Phone = 1
    COMMUNICATION_MEDIUM_CHOICES = (
        (MAIL, 'Mail'),
        (Phone, 'Phone'),
    )

    contact = models.ForeignKey('Contact',
                                related_name='communications', on_delete=models.CASCADE)
    # todo country model
    country = models.PositiveIntegerField('Country', default=1)
    subject = models.CharField('Subject', max_length=512)
    content = models.TextField('Content')
    date = models.DateField('Date', null=True, blank=True,
                            help_text='Date on which communication occurred.')
    medium = models.PositiveSmallIntegerField('Medium', choices=COMMUNICATION_MEDIUM_CHOICES)

    def __str__(self):
        return f'{self.contact} {self.date}'
