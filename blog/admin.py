from django.contrib import admin
from .models import Post, Comment   

class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created', 'updated')
    search_fields = ('title', 'content')
    list_filter = ('created', 'updated')        

admin.site.register(Post, BlogPostAdmin)
admin.site.register(Comment)