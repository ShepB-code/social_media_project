from django.shortcuts import render, redirect
from django.utils import timezone
from .forms import PostForm,ProfileForm, RelationshipForm
from .models import Post, Comment, Like, Profile, Relationship
from datetime import datetime, date, timedelta

from django.contrib.auth.decorators import login_required
from django.http import Http404


# Create your views here.

# When a URL request matches the pattern we just defined, 
# Django looks for a function called index() in the views.py file. 

def index(request):
    """The home page for Learning Log."""
    context = {}
    if not request.user.is_anonymous:
        user_profile = Profile.objects.filter(user=request.user)
        if user_profile.exists() and request.user.is_authenticated:
            # get incoming friend requests
            incoming_friend_requests = Relationship.objects.filter(receiver=Profile.objects.get(user=request.user), status='sent').count()

        
            context['incoming_friend_requests'] = incoming_friend_requests

            # get new posts from today
            
            # Calculate the time 24 hours ago from now
            one_day_ago = timezone.now() - timedelta(days=1)
            friends = Profile.objects.filter(user=request.user).values('friends')

            # Filter posts newer than 24 hours
            recent_posts = Post.objects.filter(date_posted__gte=one_day_ago, username__in=friends)

            if recent_posts.exists():
                context['recent_posts'] = recent_posts


    context['has_notifications'] = len(context) != 0
    return render(request, 'FeedApp/index.html', context)

@login_required
def profile(request):
    profile = Profile.objects.filter(user=request.user)

    if not profile.exists():
        Profile.objects.create(user=request.user)
    profile = Profile.objects.get(user=request.user)

    if request.method != 'POST':
        form = ProfileForm(instance=profile)
    else:
        form = ProfileForm(instance=profile, data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('FeedApp:profile')
        
    context = {'form': form}
    return render(request, 'FeedApp/profile.html', context)

@login_required
def myfeed(request):
    comment_count_list = []
    like_count_list = []

    posts = Post.objects.filter(username=request.user).order_by('-date_posted')

    for p in posts:
        c_count = Comment.objects.filter(post=p).count()
        l_count = Like.objects.filter(post=p).count()

        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    
    zipped_list = zip(posts, comment_count_list, like_count_list)

    context = {'posts': posts, 'zipped_list': zipped_list}
    return render(request, 'FeedApp/myfeed.html', context)

@login_required
def new_post(request):
    if request.method != 'POST':
        form = PostForm()
    else:
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.username = request.user
            new_post.save()
            return redirect('FeedApp:myfeed')
        
    context = {'form':form}

    return render(request, 'FeedApp/new_post.html', context)

@login_required
def delete_post(request, post_id):
    if request.method == 'POST':
        post = Post.objects.get(id=post_id, username=request.user)
        post.delete()
        return redirect('FeedApp:myfeed')

@login_required
def friendsfeed(request):
    comment_count_list = []
    like_count_list = []
    friends = Profile.objects.filter(user=request.user).values('friends')
    posts = Post.objects.filter(username__in=friends).order_by('-date_posted')

    for p in posts:
        c_count = Comment.objects.filter(post=p).count()
        l_count = Like.objects.filter(post=p).count()

        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    
    zipped_list = zip(posts, comment_count_list, like_count_list)

    if request.method == 'POST' and request.POST.get("like"):
        post_to_like = request.POST.get("like")
        like_already_exists = Like.objects.filter(post_id=post_to_like, username=request.user)

        if not like_already_exists.exists():
            Like.objects.create(post_id=post_to_like, username=request.user)
        else:
            Like.objects.get(post_id=post_to_like, username=request.user).delete()
        return redirect("FeedApp:friendsfeed")

        
    context = {'posts': posts, 'zipped_list': zipped_list}
    return render(request, 'FeedApp/friendsfeed.html', context)

@login_required
def comments(request, post_id):
    if request.method == 'POST':
        if request.POST.get("btn1"):
            comment = request.POST.get("comment")
            Comment.objects.create(post_id=post_id, username=request.user, text=comment, date_added=date.today())
        elif request.POST.get("btn2"):
            comment_id = request.POST.get("btn2")
            Comment.objects.get(id=comment_id).delete()

    comments = Comment.objects.filter(post=post_id)
    post = Post.objects.get(id=post_id)

    context = {'post':post, 'comments':comments}

    return render(request, 'FeedApp/comments.html', context)

@login_required
def friends(request):
    # get the admin profile and user profile to create the first relationship
    admin_profile = Profile.objects.get(user=1)
    user_profile = Profile.objects.get(user=request.user)

    # to get current friends
    user_friends = user_profile.friends.all()
    user_friends_profiles = Profile.objects.filter(user__in=user_friends)

    # get friend requests sent
    user_relationships = Relationship.objects.filter(sender=user_profile)
    request_sent_profiles = user_relationships.values('receiver')

    # to get eligible profiles for friends, exclude the user, their existing friends, and the requests sent already
    all_profiles = Profile.objects.exclude(user=request.user).exclude(id__in=user_friends_profiles).exclude(id__in=request_sent_profiles)

    # to get friend requests received by the user
    request_received_profiles = Relationship.objects.filter(receiver=user_profile, status='sent')

    # if this is the first time to access the friends page, create the first relationship with the admin
    if not user_relationships.exists():
        Relationship.objects.create(sender=user_profile, receiver=admin_profile, status='sent')

    # this is to process all send requests
    if request.method == 'POST' and request.POST.get("send_requests"):
        receivers = request.POST.getlist("send_requests")
        for receiver in receivers:
            receiver_profile = Profile.objects.get(id=receiver)
            Relationship.objects.create(sender=user_profile, receiver=receiver_profile, status='sent')
        return redirect('FeedApp:friends')
    
    if request.method == 'POST' and request.POST.get("receive_requests"):
        senders = request.POST.getlist("receive_requests")
        for sender in senders:
            # update the relationship model for the sneder to status 'accepted'
            Relationship.objects.filter(id=sender).update(status='accepted')

            # create a relationship object to access the sender's user id to add to the friends list of the user
            relationship_obj = Relationship.objects.get(id=sender)
            user_profile.friends.add(relationship_obj.sender.user)

            # add the user to the friends list of the sender's profile
            relationship_obj.sender.friends.add(request.user)
    
    context = {'user_friends_profiles': user_friends_profiles, 'user_relationships': user_relationships,
               'all_profiles': all_profiles, 'request_received_profiles': request_received_profiles}
    
    return render(request, 'FeedApp/friends.html', context)