# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
import django
from django.db import models


class WithFFactsAsSelectIdIso3(models.Model):
    iso3 = models.CharField(max_length=10)
    location = models.BigIntegerField(blank=True, null=True)
    sex = models.BigIntegerField(blank=True, null=True)
    age = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'WITH f_facts as (\n    SELECT\n        id,\n        iso3,\n        '


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthtokenToken(models.Model):
    key = models.CharField(primary_key=True, max_length=40)
    created = models.DateTimeField()
    user = models.OneToOneField('UsersUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'authtoken_token'


class Communications(models.Model):
    subject = models.TextField()
    iso3 = models.ForeignKey('GeoEntities', models.DO_NOTHING, db_column='iso3')
    contact = models.ForeignKey('Contacts', models.DO_NOTHING)
    conducted_at = models.DateField(blank=True, null=True)
    tool = models.TextField()
    content = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by',
        blank=True, null=True, related_name='communication_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'communications'


class ContactCommunication(models.Model):
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    version_id = models.CharField(max_length=16, blank=True, null=True)
    title = models.CharField(max_length=256, blank=True, null=True)
    subject = models.CharField(max_length=512)
    content = models.TextField()
    medium = models.ForeignKey('ContactCommunicationmedium', models.DO_NOTHING, blank=True, null=True)
    contact = models.ForeignKey('ContactContact', models.DO_NOTHING)
    created_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='contact_communication_created_by'
    )
    last_modified_by = models.ForeignKey('UsersUser', models.DO_NOTHING, blank=True, null=True)
    old_id = models.CharField(max_length=32, blank=True, null=True)
    attachment = models.ForeignKey('ContribAttachment', models.DO_NOTHING, blank=True, null=True)
    country = models.ForeignKey('CountryCountry', models.DO_NOTHING, blank=True, null=True)
    date = models.DateField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contact_communication'


class ContactCommunicationmedium(models.Model):
    name = models.CharField(max_length=256)

    class Meta:
        managed = False
        db_table = 'contact_communicationmedium'


class ContactContact(models.Model):
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    version_id = models.CharField(max_length=16, blank=True, null=True)
    designation = models.IntegerField()
    first_name = models.CharField(max_length=256)
    last_name = models.CharField(max_length=256)
    gender = models.IntegerField()
    job_title = models.CharField(max_length=256)
    email = models.CharField(max_length=254, blank=True, null=True)
    phone = models.CharField(unique=True, max_length=256, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    country = models.ForeignKey('CountryCountry', models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='contact_contact_created_by'
    )
    last_modified_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='contact_last_modifield_by'
    )
    organization = models.ForeignKey('OrganizationOrganization', models.DO_NOTHING, blank=True, null=True)
    old_id = models.CharField(max_length=32, blank=True, null=True)
    skype = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contact_contact'


class ContactContactCountriesOfOperation(models.Model):
    contact = models.ForeignKey(ContactContact, models.DO_NOTHING)
    country = models.ForeignKey('CountryCountry', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'contact_contact_countries_of_operation'
        unique_together = (('contact', 'country'),)


class Contacts(models.Model):
    title = models.TextField()
    name = models.TextField()
    surname = models.TextField()
    gender = models.TextField()
    organisation = models.TextField()
    job_title = models.TextField()
    countries_of_operation = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    skype = models.TextField(blank=True, null=True)
    phone = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name="contact_created_by")
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True, null=True, related_name='contact_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contacts'


class ContextualAnalysis(models.Model):
    iso3 = models.ForeignKey('GeoEntities', models.DO_NOTHING, db_column='iso3')
    publication_date = models.DateField()
    displacement_type = models.TextField()
    title = models.TextField(unique=True)
    content = models.TextField(blank=True, null=True)
    group = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='contextual_created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True, null=True, related_name='contextual_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contextual_analysis'


class ContribAttachment(models.Model):
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    version_id = models.CharField(max_length=16, blank=True, null=True)
    attachment = models.CharField(max_length=100)
    attachment_for = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='contrib_attachment_created_by'
    )
    last_modified_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='contrib_attachment_modifield_by'
    )
    encoding = models.CharField(max_length=256, blank=True, null=True)
    filetype_detail = models.CharField(max_length=256, blank=True, null=True)
    mimetype = models.CharField(max_length=256, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'contrib_attachment'


class CountryContextualupdate(models.Model):
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    version_id = models.CharField(max_length=16, blank=True, null=True)
    update = models.TextField()
    country = models.ForeignKey('CountryCountry', models.DO_NOTHING)
    created_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='country_contextual_update_created_by'
    )
    last_modified_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='country_contextualupdate_modified_by'
    )
    old_id = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'country_contextualupdate'


class CountryCountry(models.Model):
    name = models.CharField(max_length=256)
    region = models.ForeignKey('CountryCountryregion', models.DO_NOTHING)
    bounding_box = models.TextField(blank=True, null=True)  # This field type is a guess.
    centroid = models.TextField(blank=True, null=True)  # This field type is a guess.
    country_code = models.SmallIntegerField(blank=True, null=True)
    idmc_full_name = models.CharField(max_length=256, blank=True, null=True)
    idmc_short_name = models.CharField(max_length=256, blank=True, null=True)
    idmc_short_name_ar = models.CharField(max_length=256, blank=True, null=True)
    idmc_short_name_es = models.CharField(max_length=256, blank=True, null=True)
    idmc_short_name_fr = models.CharField(max_length=256, blank=True, null=True)
    iso3 = models.CharField(max_length=5, blank=True, null=True)
    sub_region = models.CharField(max_length=256, blank=True, null=True)
    geographical_group = models.ForeignKey('CountryGeographicalgroup', models.DO_NOTHING, blank=True, null=True)
    iso2 = models.CharField(max_length=4, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'country_country'


class CountryCountryregion(models.Model):
    name = models.CharField(max_length=256)

    class Meta:
        managed = False
        db_table = 'country_countryregion'


class CountryGeographicalgroup(models.Model):
    name = models.CharField(max_length=256)

    class Meta:
        managed = False
        db_table = 'country_geographicalgroup'


class CountryHouseholdsize(models.Model):
    old_id = models.CharField(max_length=32, blank=True, null=True)
    year = models.SmallIntegerField()
    size = models.FloatField()
    country = models.ForeignKey(CountryCountry, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'country_householdsize'
        unique_together = (('country', 'year'),)


class CountrySummary(models.Model):
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    version_id = models.CharField(max_length=16, blank=True, null=True)
    summary = models.TextField()
    country = models.ForeignKey(CountryCountry, models.DO_NOTHING)
    created_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='country_summary_created_by'
    )
    last_modified_by = models.ForeignKey(
        'UsersUser', models.DO_NOTHING, blank=True, null=True, related_name='country_summary_last_modifield_by'
    )
    old_id = models.CharField(max_length=32, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'country_summary'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey('UsersUser', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class Documents(models.Model):
    uuid = models.UUIDField(unique=True, blank=True, null=True)
    serial_no = models.TextField(blank=True, null=True)
    confidential = models.BooleanField(blank=True, null=True)
    name = models.TextField()
    type = models.TextField()
    publication_date = models.DateField()
    comment = models.TextField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    original_filename = models.TextField(blank=True, null=True)
    filename = models.TextField(blank=True, null=True)
    content_type = models.TextField(blank=True, null=True)
    displacement_types = django.contrib.postgres.fields.JSONField()
    countries = django.contrib.postgres.fields.JSONField()
    sources = django.contrib.postgres.fields.JSONField()
    publishers = django.contrib.postgres.fields.JSONField()
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='document_created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True, null=True, related_name='document_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)
    sources_old = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    publishers_old = django.contrib.postgres.fields.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'documents'


class DocumentsPublishers(models.Model):
    document = models.OneToOneField(Documents, models.DO_NOTHING, primary_key=True)
    publisher = models.ForeignKey('Publishers', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'documents_publishers'
        unique_together = (('document', 'publisher'),)


class DocumentsSources(models.Model):
    document = models.OneToOneField(Documents, models.DO_NOTHING, primary_key=True)
    source = models.ForeignKey('Publishers', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'documents_sources'
        unique_together = (('document', 'source'),)


class Events(models.Model):
    serial_no = models.TextField(blank=True, null=True)
    name = models.TextField()
    year = models.IntegerField()
    displacement_type = models.TextField()
    hazard_type = models.ForeignKey('HazardTypes', models.DO_NOTHING, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    start_date = django.contrib.postgres.fields.JSONField()
    end_date = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    glide_numbers = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='event_created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True, null=True, related_name='event_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)
    data_included = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'events'


class EventsGeneric(models.Model):
    source = models.TextField()
    source_id = models.TextField()
    data = models.TextField(blank=True, null=True)  # This field type is a guess.
    event = models.ForeignKey(Events, models.DO_NOTHING, blank=True, null=True)
    imported_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='imported_by', blank=True, null=True, related_name='events_generic_imported_by'
    )
    imported_at = models.DateTimeField(blank=True, null=True)
    rejected = models.BooleanField(blank=True, null=True)
    rejected_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='rejected_by', blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'events_generic'
        unique_together = (('source', 'source_id'),)


class Facts(models.Model):
    type = models.TextField()
    name = models.TextField()
    displacement_type = models.TextField()
    serial_no = models.TextField(blank=True, null=True)
    year = models.IntegerField()
    iso3 = models.ForeignKey('GeoEntities', models.DO_NOTHING, db_column='iso3')
    confidential = models.BooleanField(blank=True, null=True)
    document = models.ForeignKey(Documents, models.DO_NOTHING, blank=True, null=True)
    event = models.ForeignKey(Events, models.DO_NOTHING, blank=True, null=True)
    event_role = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', models.DO_NOTHING, blank=True, null=True)
    parent_role = models.TextField(blank=True, null=True)
    groups = django.contrib.postgres.fields.ArrayField(
        models.CharField(max_length=255, blank=True),
        size=8,
    )
    themes = models.TextField(blank=True, null=True)  # This field type is a guess.
    household_size = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    start_date = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    end_date = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    data = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    actions = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    base_id = models.BigIntegerField(blank=True, null=True)
    confidence_assessment = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    locations = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='fact_created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True, null=True, related_name='fact_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    idu = models.BooleanField()
    gsn = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'facts'


class GeoEntities(models.Model):
    iso3 = models.CharField(primary_key=True, max_length=3)
    iso = models.CharField(max_length=2, blank=True, null=True)
    country_code = models.CharField(max_length=3, blank=True, null=True)
    idmc_short_name = models.TextField()
    idmc_full_name = models.TextField()
    name = models.TextField()
    geographical_group = models.TextField(blank=True, null=True)
    region = models.TextField(blank=True, null=True)
    sub_region = models.TextField(blank=True, null=True)
    centroid = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    boundingbox = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    kampala_signed = models.BooleanField(blank=True, null=True)
    kampala_ratified = models.BooleanField(blank=True, null=True)
    sub_region_au = models.TextField(blank=True, null=True)
    idmc_short_name_es = models.TextField(blank=True, null=True)
    idmc_short_name_fr = models.TextField(blank=True, null=True)
    idmc_short_name_ar = models.TextField(blank=True, null=True)
    geographical_group_grid = models.TextField(blank=True, null=True)
    au_member = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'geo_entities'


class Groups(models.Model):
    name = models.TextField(primary_key=True)
    comment = models.TextField(blank=True, null=True)
    start_date = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    end_date = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='groups_created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True, null=True, related_name='groups_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'groups'


class HazardTypes(models.Model):
    subcategory = models.TextField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    type = models.TextField(blank=True, null=True)
    subtype = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'hazard_types'


class History(models.Model):
    entity_type = models.TextField()
    entity_id = models.BigIntegerField()
    content = django.contrib.postgres.fields.JSONField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='history_created_by')
    created_at = models.DateTimeField()
    operation = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'history'


class HouseholdSizes(models.Model):
    iso3 = models.CharField(primary_key=True, max_length=3)
    year = models.IntegerField()
    size = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'household_sizes'
        unique_together = (('iso3', 'year'),)


class MonitoringChallenges(models.Model):
    iso3 = models.CharField(max_length=3)
    date = models.DateField()
    title = models.TextField(unique=True)
    content = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='created_by', related_name='monitoring_challenges_created_by'
    )
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True,
        null=True, related_name='monitoring_challenges_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'monitoring_challenges'


class OrganizationOrganization(models.Model):
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    version_id = models.CharField(max_length=16, blank=True, null=True)
    title = models.CharField(max_length=512)
    short_name = models.CharField(max_length=64, blank=True, null=True)
    methodology = models.TextField()
    source_detail_methodology = models.TextField()

    class Meta:
        managed = False
        db_table = 'organization_organization'


class OrganizationOrganizationkind(models.Model):
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField()
    version_id = models.CharField(max_length=16, blank=True, null=True)
    title = models.CharField(max_length=256)

    class Meta:
        managed = False
        db_table = 'organization_organizationkind'


class Populations(models.Model):
    iso3 = models.OneToOneField(GeoEntities, models.DO_NOTHING, db_column='iso3', primary_key=True)
    name = models.TextField(blank=True, null=True)
    loc_id_wpp = models.TextField(blank=True, null=True)
    name_wpp = models.TextField(blank=True, null=True)
    year = models.IntegerField()
    population = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'populations'
        unique_together = (('iso3', 'year'),)


class Portfolios(models.Model):
    iso3 = models.ForeignKey(GeoEntities, models.DO_NOTHING, db_column='iso3')
    username = models.ForeignKey('Users', models.DO_NOTHING, db_column='username')
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='portfolio_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'portfolios'


class Publishers(models.Model):
    name = models.TextField()
    type = models.TextField()
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='publisher_created_by')
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by', blank=True, null=True, related_name='publisher_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)
    iso3 = models.ForeignKey(GeoEntities, models.DO_NOTHING, db_column='iso3', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'publishers'
        unique_together = (('name', 'iso3'),)


class Reviews(models.Model):
    entity_id = models.IntegerField(blank=True, null=True)
    entity_type = models.TextField(blank=True, null=True)
    status = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('Users', models.DO_NOTHING, db_column='created_by', related_name='reviews_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'reviews'


class SignificantUpdates(models.Model):
    iso3 = models.ForeignKey(GeoEntities, models.DO_NOTHING, db_column='iso3')
    date = models.DateField()
    displacement_type = models.TextField()
    title = models.TextField()
    content = models.TextField(blank=True, null=True)
    source = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='created_by', related_name='significant_updates_created_by'
    )
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='updated_by',
        blank=True, null=True, related_name='significant_updates_updated_by'
    )
    updated_at = models.DateTimeField(blank=True, null=True)
    gsn = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'significant_updates'
        unique_together = (('title', 'iso3'),)


class SqlMigrations(models.Model):
    id = models.TextField(primary_key=True)
    applied_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sql_migrations'


class TabularDatasets(models.Model):
    name = models.TextField(unique=True)
    iso3 = models.ForeignKey(GeoEntities, models.DO_NOTHING, db_column='iso3')
    displacement_type = models.TextField()
    source = models.ForeignKey(Publishers, models.DO_NOTHING, blank=True, null=True)
    document = models.ForeignKey(Documents, models.DO_NOTHING, blank=True, null=True)
    unit = models.TextField()
    url = models.TextField(blank=True, null=True)
    age_class = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        'Users', models.DO_NOTHING, db_column='created_by', related_name='tabular_dataset_created_by'
    )
    created_at = models.DateTimeField()
    locked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tabular_datasets'


class TabularDatasetsRecords(models.Model):
    parent = models.ForeignKey(TabularDatasets, models.DO_NOTHING, blank=True, null=True)
    iso3 = models.ForeignKey(GeoEntities, models.DO_NOTHING, db_column='iso3')
    event_name = models.TextField(blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    org_name = models.TextField(blank=True, null=True)
    org_accuracy = models.TextField(blank=True, null=True)
    org_lat = models.FloatField(blank=True, null=True)
    org_lon = models.FloatField(blank=True, null=True)
    dst_name = models.TextField(blank=True, null=True)
    dst_accuracy = models.TextField(blank=True, null=True)
    dst_lat = models.FloatField(blank=True, null=True)
    dst_lon = models.FloatField(blank=True, null=True)
    stock_total = models.IntegerField(blank=True, null=True)
    stock_male = models.IntegerField(blank=True, null=True)
    stock_female = models.IntegerField(blank=True, null=True)
    stock_in_camp = models.IntegerField(blank=True, null=True)
    stock_outside_camp = models.IntegerField(blank=True, null=True)
    stock_age_cat_01 = models.IntegerField(blank=True, null=True)
    stock_age_cat_02 = models.IntegerField(blank=True, null=True)
    stock_age_cat_03 = models.IntegerField(blank=True, null=True)
    new_total = models.IntegerField(blank=True, null=True)
    new_male = models.IntegerField(blank=True, null=True)
    new_female = models.IntegerField(blank=True, null=True)
    new_in_camp = models.IntegerField(blank=True, null=True)
    new_outside_camp = models.IntegerField(blank=True, null=True)
    new_age_cat_01 = models.IntegerField(blank=True, null=True)
    new_age_cat_02 = models.IntegerField(blank=True, null=True)
    new_age_cat_03 = models.IntegerField(blank=True, null=True)
    returns_total = models.IntegerField(blank=True, null=True)
    returns_male = models.IntegerField(blank=True, null=True)
    returns_female = models.IntegerField(blank=True, null=True)
    returns_in_camp = models.IntegerField(blank=True, null=True)
    returns_outside_camp = models.IntegerField(blank=True, null=True)
    returns_age_cat_01 = models.IntegerField(blank=True, null=True)
    returns_age_cat_02 = models.IntegerField(blank=True, null=True)
    returns_age_cat_03 = models.IntegerField(blank=True, null=True)
    returnees_total = models.IntegerField(blank=True, null=True)
    returnees_male = models.IntegerField(blank=True, null=True)
    returnees_female = models.IntegerField(blank=True, null=True)
    returnees_in_camp = models.IntegerField(blank=True, null=True)
    returnees_outside_camp = models.IntegerField(blank=True, null=True)
    returnees_age_cat_01 = models.IntegerField(blank=True, null=True)
    returnees_age_cat_02 = models.IntegerField(blank=True, null=True)
    returnees_age_cat_03 = models.IntegerField(blank=True, null=True)
    house_destroyed = models.IntegerField(blank=True, null=True)
    house_damaged = models.IntegerField(blank=True, null=True)
    url = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tabular_datasets_records'


class TabularDatasetsRecordsToFacts(models.Model):
    f = models.ForeignKey(Facts, models.DO_NOTHING)
    tdr = models.ForeignKey(TabularDatasetsRecords, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'tabular_datasets_records_to_facts'
        unique_together = (('f', 'tdr'),)


class TempGeoentitiesOtherLang(models.Model):
    iso3 = models.CharField(max_length=255, blank=True, null=True)
    iso = models.CharField(max_length=255, blank=True, null=True)
    country_code = models.CharField(max_length=255, blank=True, null=True)
    idmc_short_name = models.CharField(max_length=255, blank=True, null=True)
    idmc_full_name = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    geographical_group = models.CharField(max_length=255, blank=True, null=True)
    region = models.CharField(max_length=255, blank=True, null=True)
    sub_region = models.CharField(max_length=255, blank=True, null=True)
    centroid_001 = models.CharField(db_column='centroid__001', max_length=255, blank=True, null=True)
    centroid_002 = models.CharField(
        db_column='centroid__002', max_length=255, blank=True, null=True
    )
    boundingbox_001 = models.CharField(db_column='boundingbox__001', max_length=255, blank=True, null=True)
    boundingbox_002 = models.CharField(db_column='boundingbox__002', max_length=255, blank=True, null=True)
    boundingbox_003 = models.CharField(db_column='boundingbox__003', max_length=255, blank=True, null=True)
    boundingbox_004 = models.CharField(db_column='boundingbox__004', max_length=255, blank=True, null=True)
    kampala_signed = models.CharField(max_length=255, blank=True, null=True)
    kampala_ratified = models.CharField(max_length=255, blank=True, null=True)
    sub_region_au = models.CharField(max_length=255, blank=True, null=True)
    es = models.CharField(db_column='ES', max_length=255, blank=True, null=True)
    fr = models.CharField(db_column='FR', max_length=255, blank=True, null=True)
    ar = models.CharField(db_column='AR', max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'temp_geoentities_other_lang'


class Users(models.Model):
    username = models.TextField(primary_key=True)
    name = models.TextField()
    email = models.TextField(unique=True)
    password_hash = models.BinaryField(blank=True, null=True)
    admin_user = models.BooleanField(blank=True, null=True)
    failed_login_attempts = models.IntegerField(blank=True, null=True)
    suspended_at = models.DateTimeField(blank=True, null=True)
    last_login_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    permissions = django.contrib.postgres.fields.JSONField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'


class UsersUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=150)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    email = models.CharField(unique=True, max_length=254)
    username = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'users_user'


class UsersUserGroups(models.Model):
    user = models.ForeignKey(UsersUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'users_user_groups'
        unique_together = (('user', 'group'),)


class UsersUserUserPermissions(models.Model):
    user = models.ForeignKey(UsersUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'users_user_user_permissions'
        unique_together = (('user', 'permission'),)
