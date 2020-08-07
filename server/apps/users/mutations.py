import graphene
from django.contrib.auth import get_user_model, login
from graphene_django.forms.mutation import DjangoFormMutation

from apps.users.forms import LoginForm, RegisterForm
from apps.users.schema import UserType

User = get_user_model()


class RegisterMutation(DjangoFormMutation):
    class Meta:
        form_class = RegisterForm

    @classmethod
    def get_form_kwargs(cls, root, info, **input):
        kwargs = super().get_form_kwargs(root, info, **input)
        # to send activation email
        kwargs['request'] = info.context
        return kwargs


class LoginMutation(DjangoFormMutation):
    class Meta:
        form_class = LoginForm

    user = graphene.Field(UserType)

    @classmethod
    def perform_mutate(cls, form, info):
        if user := form.cleaned_data.get('user', None):
            login(info.context, user)
        return super().perform_mutate(form, info)


class Mutation(object):
    login = LoginMutation.Field()
    register = RegisterMutation.Field()
