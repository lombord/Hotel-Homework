from django import forms

from .models import Client, Booking, Room, Comment


class ClientForm(forms.ModelForm):

    class Meta:
        model = Client
        fields = '__all__'

    def save(self, commit: bool = True):
        if getattr(self, 'client_exists', None):
            return self.Meta.model.objects.get(**self.cleaned_data)
        return super().save(commit=commit)

    def is_valid(self) -> bool:
        tmp = super().is_valid()
        if not tmp and len(self.base_fields) == len(self.cleaned_data):
            self.client_exists = True
            return True
        return tmp


class RoomForm(forms.ModelForm):

    class Meta:
        model = Room
        exclude = 'slug', 'is_liked'


class BookingForm(forms.ModelForm):

    class Meta:
        model = Booking
        exclude = ['approve_status', 'client', 'total_price']
        widgets = {
            'room': forms.HiddenInput(),
            'start_book': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_book': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        exclude = 'room',
        widgets = {
            'content': forms.Textarea(attrs={'rows': 5})
        }
        labels = {'content': 'Comment'}
