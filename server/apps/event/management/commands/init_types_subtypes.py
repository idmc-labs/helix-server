
from django.core.management.base import BaseCommand

from apps.event.constants import VIOLENCES, TRIGGERS, SUB_TRIGGERS, DISASTERS
from apps.event.models import (
    Violence,
    ViolenceSubType,
    Trigger,
    TriggerSubType,
    DisasterCategory,
    DisasterSubCategory,
    DisasterType,
    DisasterSubType,
)


class Command(BaseCommand):
    help = 'Initialize or update event types.'

    def handle(self, *args, **options):
        for v_type, v_sub_types in VIOLENCES.items():
            if Violence.objects.filter(name__iexact=v_type).exists():
                violence = Violence.objects.get(name__iexact=v_type)
            else:
                violence = Violence.objects.create(name=v_type)

            for sub_type in v_sub_types:
                if not ViolenceSubType.objects.filter(name__iexact=sub_type, violence__name__iexact=violence.name).exists():
                    violence_sub_type = ViolenceSubType.objects.create(name=sub_type, violence=violence)
                else:
                    violence_sub_type = ViolenceSubType.objects.get(
                        name__iexact=sub_type, violence__name__iexact=violence.name)
                violence_sub_type.save()
        self.stdout.write(self.style.SUCCESS('Saved {} violences with {} violences sub types.'.format(
            Violence.objects.count(),
            ViolenceSubType.objects.count()
        )))
        for trigger_name in TRIGGERS:
            if Trigger.objects.filter(name__iexact=trigger_name).exists():
                Trigger.objects.get(name__iexact=trigger_name)
            else:
                Trigger.objects.create(name=trigger_name)
        self.stdout.write(self.style.SUCCESS('Saved {} triggers.'.format(
            Trigger.objects.count(),
        )))
        for sub_trigger_name in SUB_TRIGGERS:
            if TriggerSubType.objects.filter(name__iexact=sub_trigger_name).exists():
                TriggerSubType.objects.get(name__iexact=sub_trigger_name)
            else:
                TriggerSubType.objects.create(name=sub_trigger_name)
        self.stdout.write(self.style.SUCCESS('Saved {} trigger sub types.'.format(
            TriggerSubType.objects.count(),
        )))

        # disasters
        for cat in DISASTERS:
            # cats
            if DisasterCategory.objects.filter(name__iexact=cat).exists():
                category = DisasterCategory.objects.get(name__iexact=cat)
            else:
                category = DisasterCategory.objects.create(name=cat)
            # sub cats
            for subcat in DISASTERS[cat]:
                if DisasterSubCategory.objects.filter(name__iexact=subcat, category__name__iexact=category.name).exists():
                    sub_category = DisasterSubCategory.objects.get(name__iexact=subcat, category__name__iexact=category.name)
                else:
                    sub_category = DisasterSubCategory.objects.create(name=subcat, category=category)
                for dtype in DISASTERS[cat][subcat]:
                    # disaster types
                    if DisasterType.objects.filter(name__iexact=dtype,
                                                   disaster_sub_category__name__iexact=sub_category.name).exists():
                        disaster_type = DisasterType.objects.get(
                            name__iexact=dtype, disaster_sub_category__name__iexact=sub_category.name)
                    else:
                        disaster_type = DisasterType.objects.create(name=dtype, disaster_sub_category=sub_category)
                    # disaster sub types
                    for dsubtype in DISASTERS[cat][subcat][dtype]:
                        if DisasterSubType.objects.filter(name__iexact=dsubtype,
                                                          type__name__iexact=disaster_type.name).exists():
                            disaster_sub_type = DisasterSubType.objects.get(
                                name__iexact=dsubtype, type__name__iexact=disaster_type.name)
                        else:
                            disaster_sub_type = DisasterSubType.objects.create(name=dsubtype, type=disaster_type)
        self.stdout.write(self.style.SUCCESS('Saved {} disaster categories.'.format(
            DisasterCategory.objects.count(),
        )))
        self.stdout.write(self.style.SUCCESS('Saved {} disaster sub categories.'.format(
            DisasterSubCategory.objects.count(),
        )))
        self.stdout.write(self.style.SUCCESS('Saved {} disaster types.'.format(
            DisasterType.objects.count(),
        )))
        self.stdout.write(self.style.SUCCESS('Saved {} disaster subtypes.'.format(
            DisasterSubType.objects.count(),
        )))
