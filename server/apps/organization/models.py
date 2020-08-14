from django.db import models


class OrganizationType(models.Model):
    title = models.CharField('Title', max_length=256)


class Organization(models.Model):
    title = models.CharField('Title', max_length=512)
    short_name = models.CharField('Short Name', max_length=64,
                                  null=True)
    # logo =
    organization_type = models.ForeignKey('OrganizationType', null=True,
                                          on_delete=models.SET_NULL)
    methodology = models.TextField('Methodology', help_text='')
    source_detail_methodology = models.TextField('Source detail and methodology',
                                                 help_text='')
    parent = models.ForeignKey('Organization', null=True, blank=True,
                               on_delete=models.CASCADE, related_name='sub_organizations')

    def __str__(self):
        return self.title
