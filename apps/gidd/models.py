from django.db import models
from django.utils.translation import gettext_lazy as _


class Conflict(models.Model):
    country = models.ForeignKey(
        'country.Country', related_name='country_conflict', on_delete=models.PROTECT,
        verbose_name=_('Country'), null=True, blank=True
    )
    year = models.BigIntegerField()
    total_displacement = models.BigIntegerField(blank=True, null=True)

    total_displacement_source = models.TextField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement_source = models.TextField(blank=True, null=True)
    returns = models.BigIntegerField(blank=True, null=True)
    returns_source = models.TextField(blank=True, null=True)
    local_integration = models.BigIntegerField(blank=True, null=True)
    local_integration_source = models.TextField(blank=True, null=True)
    resettlement = models.BigIntegerField(blank=True, null=True)
    resettlement_source = models.TextField(blank=True, null=True)
    cross_border_flight = models.BigIntegerField(blank=True, null=True)
    cross_border_flight_source = models.TextField(blank=True, null=True)
    children_born_to_idps = models.BigIntegerField(blank=True, null=True)
    children_born_to_idps_source = models.TextField(blank=True, null=True)
    idp_deaths = models.BigIntegerField(blank=True, null=True)
    idp_deaths_source = models.TextField(blank=True, null=True)

    # TODO: Should we change these fields to DateField?
    total_displacement_since = models.TextField(blank=True, null=True)
    new_displacement_since = models.TextField(blank=True, null=True)
    returns_since = models.TextField(blank=True, null=True)
    resettlement_since = models.TextField(blank=True, null=True)
    local_integration_since = models.TextField(blank=True, null=True)
    cross_border_flight_since = models.TextField(blank=True, null=True)
    children_born_to_idps_since = models.TextField(blank=True, null=True)
    idp_deaths_since = models.TextField(blank=True, null=True)
    old_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Conflict')
        verbose_name_plural = _('Conflicts')

    def __str__(self):
        return str(self.year)


class Disaster(models.Model):
    country = models.ForeignKey(
        'country.Country', related_name='country_disaster', on_delete=models.PROTECT,
        verbose_name=_('Country'), null=True, blank=True
    )
    year = models.BigIntegerField()
    glide_number = models.TextField(blank=True, null=True)
    event_name = models.TextField(blank=True, null=True)
    location_text = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    start_date_accuracy = models.TextField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_date_accuracy = models.TextField(blank=True, null=True)
    hazard_category = models.TextField(blank=True, null=True)
    hazard_sub_category = models.TextField(blank=True, null=True)
    hazard_sub_type = models.TextField(blank=True, null=True)
    hazard_type = models.TextField(blank=True, null=True)
    new_displacement = models.BigIntegerField(blank=True, null=True)
    new_displacement_source = models.TextField(blank=True, null=True)
    new_displacement_since = models.TextField(blank=True, null=True)
    old_id = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Disaster')
        verbose_name_plural = _('Disasters')

    def __str__(self):
        return str(self.year)
