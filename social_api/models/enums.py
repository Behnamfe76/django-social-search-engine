"""Shared enum choices.

``EmailType`` and ``PhoneType`` have no table of their own yet; they are declared
here so the email/phone tables can adopt them unchanged when they land.
"""

from django.db import models


class GenderType(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"
    UNKNOWN = "unknown", "Unknown"


class EmailType(models.TextChoices):
    PERSONAL = "personal", "Personal"
    PROFESSIONAL = "professional", "Professional"
    CURRENT_PROFESSIONAL = "current_professional", "Current professional"
    DISPOSABLE = "disposable", "Disposable"
    OTHER = "other", "Other"


class PhoneType(models.TextChoices):
    MOBILE = "mobile", "Mobile"
    HOME = "home", "Home"
    WORK = "work", "Work"
    OTHER = "other", "Other"
