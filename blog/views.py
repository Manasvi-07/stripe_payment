# blog/views.py
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import Post, Comment
from payments.models import Subscription

class PostListView(ListView):
    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    ordering = ['-created']

class PostCreateView(CreateView):
    model = Post
    fields = ['title', 'content', 'image']
    template_name = 'blog/post_form.html'
    success_url = reverse_lazy('post_list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)
       
class PostDetailView(LoginRequiredMixin, DetailView):
    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        user = self.request.user

        context['comments'] = post.comments.all().order_by('created')

        if user.is_authenticated:
            context['user_comment_count'] = Comment.objects.filter(post=post, author=user).count()
            context['user_has_subscription'] = user.has_active_subscription
        else:
            context['user_comment_count'] = 0
            context['user_has_subscription'] = False

        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user = request.user
        content = request.POST.get('content')

        if not user.is_authenticated or not content:
            return redirect('post_detail', pk=self.object.pk)

        can_comment = user.has_active_subscription or Comment.objects.filter(post=self.object, author=user).count() < 2
        if can_comment:
            Comment.objects.create(post=self.object, author=user, content=content)
            messages.success(request, "Comment added successfully!")
        else:
            messages.error(request, "You have reached the limit of 2 free comments on this post. Subscribe to comment more.")

        return redirect('post_detail', pk=self.object.pk)
    
class PostUpdateView(UpdateView):
    model = Post
    fields = ['title', 'content', 'image']
    template_name = 'blog/post_form.html'
    success_url = reverse_lazy('post_list')

class PostDeleteView(DeleteView):
    model = Post
    template_name = 'blog/post_confirm_delete.html'
    success_url = reverse_lazy('post_list')

class AddCommentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        user = request.user
        content = request.POST.get("content")

        if user.has_active_subscription:
            can_comment = True
        else:
            user_comment_count = Comment.objects.filter(post=post, author=user).count()
            can_comment = user_comment_count < 2

        if not can_comment:
            messages.error(
                request,
                "You have reached the limit of 2 free comments on this post. Subscribe to comment more."
            )
            return redirect("post_detail", pk=post.pk)

        if content:
            Comment.objects.create(post=post, author=user, content=content)
            messages.success(request, "Comment added successfully!")

        return redirect("post_detail", pk=post.pk)

    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        return render(request, 'blog/add_comment.html', {'post': post})