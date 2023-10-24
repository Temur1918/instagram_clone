from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MaxLengthValidator
from django.db.models import UniqueConstraint

from shared_app.models import BaseModel

User = get_user_model() # Asosiy user modelini olish

class Post(BaseModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')   # user modelini ulash
    image = models.ImageField(upload_to="post_photos/", validators=[FileExtensionValidator(  # yuklanadigan rasm formatlarini ko'rsatish
        allowed_extensions=['png', 'jpg', 'jpeg']
    )])
    caption = models.TextField(validators=[MaxLengthValidator(2000)])  # Kiritiladigan text uzunligini belgilash    

    class Meta:
        db_table = "posts"   # Malumotlar bazasida jadval nomi
        verbose_name = "post" # qisqartirilgan nomi
        verbose_name_plural = "posts"  # uzun nomi

    def __str__(self):
        return f"{self.author} --> {self.caption}"

class PostComment(BaseModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    comment = models.TextField(validators=[MaxLengthValidator(1000)])
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='child',
        null=True,
        blank=True
    ) 

    def __str__(self):
        return f"{self.author.get_username()} --> {self.comment}"


class PostLike(BaseModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['author', 'post'],    # Bitta author bitta like bosishini taminlaydi
                name = "PostLikeUnique"
            )
        ]

    def __str__(self):
        return self.author.get_username()


class CommentLike(BaseModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(PostComment, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['author', 'comment'],     # Bitta author bitta like bosishini taminlaydi
                name = "CommentLikeUnique"
            )
        ]

    def __str__(self):
        return f"{self.author} --> {self.comment}"