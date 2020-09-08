class MetaInformationSerializerMixin(object):
    """
    Responsible to add following fields into the validated data
    - created_by
    - last_modified_by
    """
    def validate(self, attrs) -> dict:
        attrs = super().validate(attrs)
        if self.instance is None:
            attrs.update({
                'created_by': self.context['request'].user
            })
        else:
            attrs.update({
                'last_modified_by': self.context['request'].user
            })
        return attrs
