from django.db import models
from django.conf import settings
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
import os
from .utils import user_directory_path

class Category(models.Model):
    name = models.CharField(max_length = 200)

    def __str__(self):
        return self.name
    
class Post(models.Model):
    title = models.CharField(max_length = 200)
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL,related_name = 'posts',on_delete = models.CASCADE)
    created = models.DateTimeField(auto_now_add = True)
    updated = models.DateTimeField(auto_now = True)
    image = models.ImageField(upload_to = user_directory_path, blank=True, null=True)
    category = models.ForeignKey(Category, related_name = 'posts', on_delete = models.SET_NULL, null = True, blank = True)

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.pk:
            old_post = Post.objects.filter(pk=self.pk).first()
            if old_post and old_post.image and old_post.image != self.image:
                old_image_path = old_post.image.path
                if os.path.isfile(old_image_path):
                    os.remove(old_image_path)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)
    
class Comment(models.Model):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL,related_name='comments',on_delete=models.CASCADE)
    content = models.TextField()
    created = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return self.post.title