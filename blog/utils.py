import datetime

def user_directory_path(instance, filename):
    now = datetime.datetime.now()
    return f'posts/user_{instance.author.id}/{now.strftime("%Y/%m/%d")}/{filename}'
