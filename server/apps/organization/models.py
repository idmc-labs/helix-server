from django.db import models


class OrganizationKind(models.Model):
    title = models.CharField('Title', max_length=256)


class Organization(models.Model):
    title = models.CharField('Title', max_length=512)
    short_name = models.CharField('Short Name', max_length=64,
                                  null=True)
    # logo =
    organization_type = models.ForeignKey('OrganizationKind', blank=True, null=True,
                                          on_delete=models.SET_NULL,
                                          related_name='organizations')
    methodology = models.TextField('Methodology', help_text='')
    source_detail_methodology = models.TextField('Source detail and methodology',
                                                 help_text='')
    parent = models.ForeignKey('Organization', null=True, blank=True,
                               on_delete=models.CASCADE, related_name='sub_organizations')

    def __str__(self):
        return self.title
