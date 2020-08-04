import graphene

from graphql_auth.schema import UserQuery, MeQuery
from graphql_auth import relay


# https://django-graphql-auth.readthedocs.io/en/latest/installation/#1-schema
class AuthRelayMutation(graphene.ObjectType):
    register = relay.Register.Field()
    verify_account = relay.VerifyAccount.Field()
    resend_activation_email = relay.ResendActivationEmail.Field()
    send_password_reset_email = relay.SendPasswordResetEmail.Field()
    password_reset = relay.PasswordReset.Field()
    password_change = relay.PasswordChange.Field()
    update_account = relay.UpdateAccount.Field()
    # archive_account = relay.ArchiveAccount.Field()
    # delete_account = relay.DeleteAccount.Field()
    # send_secondary_email_activation = relay.SendSecondaryEmailActivation.Field()
    # verify_secondary_email = relay.VerifySecondaryEmail.Field()
    # swap_emails = relay.SwapEmails.Field()
    # remove_secondary_email = relay.RemoveSecondaryEmail.Field()

    # django-graphql-jwt inheritances
    token_auth = relay.ObtainJSONWebToken.Field()
    verify_token = relay.VerifyToken.Field()
    refresh_token = relay.RefreshToken.Field()
    revoke_token = relay.RevokeToken.Field()


class Query(UserQuery,
            MeQuery,
            graphene.ObjectType):
    pass


class Mutation(AuthRelayMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
