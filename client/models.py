from decimal import Decimal

from django.utils import timezone
from django.db import models
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class InitModelMixin():
    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            self.init_instance()
            super().save()

    def init_instance(self):
        pass


class Client(models.Model):
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)

    class Meta:
        constraints = [models.UniqueConstraint
                       (name='client_unique',
                        fields=['first_name', 'middle_name', 'last_name'],
                        violation_error_message=_(
                            "Client should be unique!"))]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Room(InitModelMixin, models.Model):
    ROOM_TYPES = (
        (1, "Average"),
        (2, "Comfort"),
        (3, "VIP"),
    )

    room_type = models.DecimalField(
        max_digits=1, decimal_places=0, choices=ROOM_TYPES, default=1)
    slug = models.SlugField(max_length=255, default="",
                            blank=True)
    price = models.DecimalField(max_digits=19, decimal_places=2)
    image = models.ImageField(
        upload_to="rooms/%Y/%m/%d/", default="defaults/default.png")
    description = models.TextField(blank=True, default="")
    is_hidden = models.BooleanField(blank=True, default=False)
    is_liked = models.BooleanField(blank=True, default=False)

    class Meta:
        constraints = [models.UniqueConstraint
                       (name='slug_unique',
                        fields=['slug',],
                        violation_error_message=_(
                            "Slug field must be unique!"))]
        ordering = '-pk',

    def get_absolute_url(self, url_name='room'):
        return reverse(url_name, kwargs={"slug": self.slug})

    def init_instance(self):
        if not self.slug:
            self.slug = slugify(f"{self.get_room_type_display()} {self.pk}")

    def __str__(self) -> str:
        return f"{self.get_room_type_display()}: {self.price}$ per day"


class Comment(models.Model):
    content = models.TextField()
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name='comments')
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = '-created',

    def __str__(self) -> str:
        return self.content[:50]


class Service(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=19, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.title}: {self.price}$"


class Booking(models.Model):
    APPROVE_CHOICES = (
        (0, "Pending"),
        (1, "Approved"),
        (2, "Rejected"),
    )

    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="bookings")
    room = models.OneToOneField(
        Room, on_delete=models.CASCADE, related_name="booking")
    services = models.ManyToManyField(Service,
                                      blank=True,
                                      related_name="bookings")
    start_book = models.DateTimeField(validators=[
        MinValueValidator(timezone.now,
                          _("Start date must be in the future")),])
    end_book = models.DateTimeField(validators=[
        MinValueValidator(timezone.now,
                          _("End date must be in the future")),])
    total_price = models.DecimalField(
        max_digits=19, decimal_places=2, default=0)
    approve_status = models.DecimalField(
        max_digits=1, decimal_places=0, choices=APPROVE_CHOICES, default=0)

    def get_absolute_url(self, url_name='booking'):
        return reverse(url_name, kwargs={'pk': self.pk})

    def accept_request(self):
        self.approve_status = 1
        self.save()

    def reject_request(self):
        self.approve_status = 2
        self.save()

    def clean(self):
        if self.start_book >= self.end_book:
            raise ValidationError(
                _("Invalid booking dates. Please ensure that the start booking date is not later than the end booking date"))

    def calculate_total_price(self):
        services_price = self.get_services_price()
        room_price = self.get_room_price()
        self.total_price = room_price + services_price
        self.save()

    def get_services_price(self):
        if self.services.exists():
            return self.services.aggregate(
                total=models.Sum('price')).get('total') or 0
        return 0

    def get_days(self):
        return (self.end_book - self.start_book).days

    def get_room_price(self):
        return self.room.price * self.get_days_decimal()

    def get_days_decimal(self):
        return Decimal((self.end_book - self.start_book).total_seconds()/60**2/24)

    def __str__(self) -> str:
        return f"{self.client} booked {self.room}"
