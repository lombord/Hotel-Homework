from django.urls import path, include

from .views import *

admin_urls = [
    path('', AdminHomeView.as_view(), name='home'),
    path('add-room/', AddRoomView.as_view(), name='add_room'),
    path('rooms/', AdminRoomsView.as_view(), name='rooms'),
    path('hide-room/<slug:slug>/',
         HideRoomView.as_view(), name='hide_room'),
    path('unhide-room/<slug:slug>/',
         UnhideRoomView.as_view(), name='unhide_room'),
    path('delete-room/<slug:slug>/',
         DeleteRoomView.as_view(), name='delete_room'),
    path('requests/', include([
         path('', AdminRequestsView.as_view(), name='requests'),
         path('<int:pk>/', RequestView.as_view(), name='request'),
         path('<int:pk>/accept', AcceptRequestView.as_view(), name='accept_request'),
         path('<int:pk>/reject', RejectRequestView.as_view(), name='reject_request'),
         ],
    ))]

urlpatterns = [
    # Client url patterns
    path('', ClientHomeView.as_view(), name='home'),
    path('rooms/', include([
        path('', ClientRoomsView.as_view(), name='rooms'),
        path('favorites/', ClientFavoritesView.as_view(), name='favorites'),
        path('bookings/', ClientBookedView.as_view(), name='bookings'),
        path('<slug:slug>/', RoomView.as_view(), name='room'),
        path('<slug:slug>/like-room/', LikeRoomView.as_view(), name='like_room'),
        path('<slug:slug>/unlike-room/',
             UnLikeRoomView.as_view(), name='unlike_room'),
        path('<slug:slug>/post-comment/',
             PostCommentView.as_view(), name='post_comment'),
    ])),
    path('booking-room/', ClientBookingFormView.as_view(), name="booking_room"),
    path('delete-booking/<int:pk>/',
         DeleteBooking.as_view(), name='delete_booking'),
    # Admin url patterns
    path('hotel-admins/', include((admin_urls, 'hotel_admin'),)),
]
