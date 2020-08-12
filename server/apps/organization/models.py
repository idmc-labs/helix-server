from django.db import models


class Organization(models.Model):
    title = models.CharField('Title', max_length=512)
    methodology = models.TextField('Methodology', help_text='')
    source_detail_methodology = models.TextField('Source detail and methodology',
                                                 help_text='')
    parent = models.ForeignKey('Organization', null=True, blank=True,
                               on_delete=models.CASCADE, related_name='sub_organizations')

    def __str__(self):
        return self.title
