# clean_whitespace.py

from django.db import connection, models
from django.apps import apps
import re

def collapse_spaces(value):
    """Removes leading, trailing, and extra internal spaces."""
    return re.sub(r'\s+', ' ', value.strip())

def clean_all_whitespace():
    for model in apps.get_models():
        model_name = model.__name__
        print('STEP 0')
        print(f"Cleaning model: {model_name}")
        print('STEP 1')
        fields = [f.name for f in model._meta.fields if isinstance(f, (models.CharField, models.TextField)) and f.name!='phone']
        print(fields)
        if not fields:
            continue

        for obj in model.objects.all():
            changed = False
            for field in fields:
                value = getattr(obj, field)
                if isinstance(value, str) and value.strip() != value or '  ' in value:
                    cleaned = collapse_spaces(value)
                    setattr(obj, field, cleaned)
                    changed = True
            if changed:
                obj.save()
