import graphene


class EnumDescription(graphene.Scalar):
    # NOTE: This is for Field only. Not usable as InputField or Argument.
    # XXX: Maybe there is a better way then this.
    """
    The `EnumDescription` scalar type represents of Enum description data, represented as UTF-8
    character sequences. The String type is most often used by GraphQL to
    represent free-form human-readable text.
    """

    @staticmethod
    def coerce_string(value):
        """
        Here value should always be callable get_FOO_display
        """
        if callable(value):
            return value()
        return value

    serialize = coerce_string
    parse_value = coerce_string
    parse_literal = graphene.String.parse_literal
