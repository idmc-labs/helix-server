from django.contrib.auth import get_user_model
from graphene import Field
from graphene.types.utils import get_type
from graphene_django import DjangoObjectType
from graphene_django_extras import PageGraphqlPagination

from utils.fields import DjangoPaginatedListObjectField

User = get_user_model()

EntryListType = get_type('apps.entry.schema.EntryListType')


class UserType(DjangoObjectType):
    class Meta:
        model = User
        exclude = ('password',)

    review_entries = DjangoPaginatedListObjectField(EntryListType,
                                                    pagination=PageGraphqlPagination(
                                                        page_size_query_param='pageSize'
                                                    ), accessor='review_entries')
    created_entry = DjangoPaginatedListObjectField(EntryListType,
                                                   pagination=PageGraphqlPagination(
                                                       page_size_query_param='pageSize'
                                                   ), accessor='created_entry')


class Query(object):
    me = Field(UserType)

    def resolve_me(self, info, **kwargs):
        if info.context.user.is_authenticated:
            return info.context.user
        return None
