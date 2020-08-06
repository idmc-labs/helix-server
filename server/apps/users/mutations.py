import graphene
from django.contrib.auth import get_user_model, login
from graphene_django.forms.mutation import DjangoFormMutation

from apps.users.forms import LoginForm
from apps.users.schema import UserType

User = get_user_model()


class LoginMutation(DjangoFormMutation):
    class Meta:
        form_class = LoginForm

    user = graphene.Field(UserType)

    @classmethod
    def perform_mutate(cls, form, info):
        if user := form.cleaned_data.get('user', None):
            print('form has the user', user)
            login(info.context, user)
        return super().perform_mutate(form, info)


class Mutation(object):
    login = LoginMutation.Field()
