from django.urls import path
from . import views

app_name = 'FeedApp'

urlpatterns = [
    path('', views.index, name='index'),
    path('profile/', views.profile, name='profile'),
    path('myFeed', views.myfeed, name='myfeed'),
    path('new_post/', views.new_post, name='new_post'),
    path('delete_post/<int:post_id>/', views.delete_post, name='delete_post'),
    path('friendsfeed', views.friendsfeed, name='friendsfeed'),
    path('comments/<int:post_id>/', views.comments, name='comments'),
    path('friends/', views.friends, name='friends'),
    ]

    