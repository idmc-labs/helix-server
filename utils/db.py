from django.db import models


class Array(models.Func):
    template = '%(function)s[%(expressions)s]'
    function = 'ARRAY'
