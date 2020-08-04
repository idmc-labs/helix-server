import graphene
from graphene_django import DjangoConnectionField
from graphene_django.types import DjangoObjectType

from .models import Ship


class ShipType(DjangoObjectType):
    class Meta:
        model = Ship


class Query(object):
    all_ships = graphene.List(ShipType, description="All the ships.")

    def resolve_all_ships(self, info, **kwargs):
        return Ship.objects.all()
