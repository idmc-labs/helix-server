from django.contrib import admin

from apps.review.models import Review, ReviewComment

admin.site.register(Review)
admin.site.register(ReviewComment)
