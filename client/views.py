from django.http import HttpResponseRedirect
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (TemplateView, RedirectView,
                                  CreateView, DetailView, ListView)

from .forms import *

from .models import *


client_menu = [
    {'name': 'home', 'label': 'Home'},
    {'name': 'rooms', 'label': 'Rooms'},
    {'name': 'favorites', 'label': 'Favorites'},
]

admin_menu = [
    {'name': 'hotel_admin:home', 'label': 'Home'},
    {'name': 'hotel_admin:rooms', 'label': 'Rooms'},
    {'name': 'hotel_admin:requests', 'label': 'Requests'},
    {'name': 'hotel_admin:add_room', 'label': 'Add Room'},
]


class BaseMixin():
    menu = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["menu"] = self.get_menu()
        return context

    def get_menu(self):
        return self.menu.copy()


class ClientBaseMixin(BaseMixin):
    menu = client_menu

    def get_menu(self):
        menu = super().get_menu()
        if Booking.objects.exists():
            menu.append({'name': 'bookings', 'label': 'Bookings'})
        return menu


class AdminBaseMixin(BaseMixin):
    menu = admin_menu


class BaseHomeView(TemplateView):
    template_name = 'client/base/home.html'


class ClientHomeView(ClientBaseMixin, BaseHomeView):
    extra_context = {'title': 'Home Page'}


class AdminHomeView(AdminBaseMixin, BaseHomeView):
    extra_context = {'title': 'Admin Home Page'}


class BaseRoomsView(ListView):
    model = Room
    context_object_name = 'list'
    extra_context = {'title': 'Available Rooms'}


class ClientRoomsView(ClientBaseMixin, BaseRoomsView):
    template_name = 'client/client/rooms.html'

    def get_queryset(self):
        queryset = self.model.objects.annotate(
            reserved=Exists(Booking.objects.filter(room=OuterRef('pk'))))
        return queryset.filter(reserved=False, is_hidden=False)


class ClientFavoritesView(ClientRoomsView):
    extra_context = {'title': 'Favorite Rooms'}

    def get_queryset(self):
        return super().get_queryset().filter(is_liked=True)


class AdminRoomsView(AdminBaseMixin, BaseRoomsView):
    template_name = 'client/admin/rooms.html'


class BaseBookedView(ListView):
    model = Booking
    context_object_name = 'list'
    extra_context = {'title': 'Booked Rooms'}


class ClientBookedView(ClientBaseMixin, BaseBookedView):
    template_name = 'client/client/bookings.html'


class AdminRequestsView(AdminBaseMixin, BaseBookedView):
    template_name = 'client/admin/bookings.html'
    allow_empty = True
    extra_context = {'title': 'Requests'}

    def get_queryset(self):
        return self.model.objects.filter(approve_status=0)


class RequestView(AdminBaseMixin, DetailView):
    model = Booking
    template_name = 'client/admin/booking.html'
    context_object_name = 'book'


class RoomView(ClientBaseMixin, DetailView):
    model = Room
    template_name = 'client/client/room.html'
    context_object_name = 'room'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        booking = getattr(obj, 'booking', None)
        if booking:
            obj.reserved = booking.approve_status == 1
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comments'] = self.object.comments.all()
        context['form'] = CommentForm()
        return context


class MultipleFormView(TemplateView):
    forms: list[dict] = None
    success_url = None
    no_commit = {}

    def post(self, request, *args, **kwargs):
        forms = self.get_forms()
        if self.is_all_valid(forms):
            self.objects = self.save_all(forms)
            return self.forms_valid(forms=forms)
        return self.forms_invalid(forms=forms)

    def forms_valid(self, forms=None):
        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, forms=None):
        return self.render_to_response(self.get_context_data(forms=forms))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['forms'] = kwargs.get('forms') or self.get_forms()
        return context

    def get_success_url(self):
        return self.success_url

    def get_forms(self):
        statics = None
        if self.request.POST:
            statics = {'data': self.request.POST,
                       'files': self.request.FILES}
        return {data['prefix']: self.get_form_for(data, statics)
                for data in self.forms}

    def get_form_for(self, data: dict, statics: dict = None):
        statics: dict = statics or {}
        form_class: type = data['form_class']
        prefix: str = data['prefix']
        try:
            initial = getattr(self, f"get_{prefix}_initial")()
        except:
            initial = {}
        return form_class(prefix=prefix, initial=initial, **statics)

    def is_all_valid(self, forms):
        return all(tuple(form.is_valid() for form in forms.values()))

    def save_all(self, forms):
        return {prefix:
                form.save(commit=prefix not in self.no_commit)
                for prefix, form in forms.items()}


class ClientBookingFormView(ClientBaseMixin, MultipleFormView):
    forms = [
        {'form_class': ClientForm, 'prefix': 'client'},
        {'form_class': BookingForm, 'prefix': 'booking'}]
    no_commit = {'booking', }
    template_name = "client/forms/forms.html"
    success_url = reverse_lazy('bookings')
    extra_context = {'title': 'Booking a Room',
                     'submit': 'book'}

    def forms_valid(self, forms=None):
        client, booking = self.objects['client'], self.objects['booking']
        booking.client = client
        booking.save()
        forms['booking'].save_m2m()
        booking.calculate_total_price()
        return super().forms_valid(forms)

    def get_booking_initial(self):
        return {'room': self.request.GET.get('room')}


class AddRoomView(AdminBaseMixin, CreateView):
    model = Room
    form_class = RoomForm
    template_name = 'client/forms/form.html'
    success_url = reverse_lazy('hotel_admin:rooms')
    extra_context = {'title': 'Add Room', 'submit': 'Add',
                     'send_file': True}


class ObjectRedirectView(RedirectView):
    model = None
    slug_url_kwarg = 'slug'
    pk_url_kwarg = 'pk'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object(*args, **kwargs)
        self.before_redirect()
        return super().post(request, *args, **kwargs)

    def get_object(self, *args, **kwargs):
        slug = kwargs.get(self.slug_url_kwarg)
        if slug:
            return get_object_or_404(self.model, slug=slug)
        pk = kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(self.model, pk=pk)

    def get_redirect_url(self, *args, **kwargs):
        return (super().get_redirect_url() or
                self.request.META.get('HTTP_REFERER'))

    def before_redirect(self):
        pass


class LikeRoomView(ObjectRedirectView):
    model = Room

    def before_redirect(self):
        self.object.is_liked = True
        self.object.save()


class UnLikeRoomView(ObjectRedirectView):
    model = Room

    def before_redirect(self):
        self.object.is_liked = False
        self.object.save()


class PostCommentView(ObjectRedirectView):
    model = Room
    form_class = CommentForm

    def before_redirect(self):
        form = self.form_class(self.request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.room = self.object
            comment.save()


class HideRoomView(ObjectRedirectView):
    model = Room

    def before_redirect(self):
        self.object.is_hidden = True
        self.object.save()


class UnhideRoomView(ObjectRedirectView):
    model = Room

    def before_redirect(self):
        self.object.is_hidden = False
        self.object.save()


class AcceptRequestView(ObjectRedirectView):
    model = Booking
    pattern_name = 'hotel_admin:requests'

    def before_redirect(self):
        self.object.accept_request()


class RejectRequestView(ObjectRedirectView):
    model = Booking
    pattern_name = 'hotel_admin:requests'

    def before_redirect(self):
        self.object.reject_request()


class ObjectDeleteView(ObjectRedirectView):
    def before_redirect(self):
        self.object.delete()


class DeleteRoomView(ObjectDeleteView):
    model = Room


class DeleteBooking(ObjectDeleteView):
    model = Booking
