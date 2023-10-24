from rest_framework import serializers

from post.models import CommentLike, Post, PostComment, PostLike
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'photo')


class PostSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)
    post_likes_count = serializers.SerializerMethodField('get_post_likes_count') # SerializersMethodField funksiyani chaqirish
    post_comment_count = serializers.SerializerMethodField('get_post_comment_count')
    me_liked = serializers.SerializerMethodField('get_me_liked')

    class Meta:
        model = Post
        fields = ("id", "author", "image", "caption", "created_time", "post_likes_count", "post_comment_count", "me_liked")
        extra_kwargs = {"image": {"required": False}}  # Har safar Update qilganda rasmni qayta yuklamaslik uchun

    def get_post_likes_count(self, object):  # funksiya related namedagi likes orqali likelar sonioni olib beradi (Reverse relationship)
        return object.likes.count()
    
    def get_post_comment_count(self, object):  # comments soni
        return object.comments.count()
    
    def get_me_liked(self, object):
        """Request user postga like bosganmi yumi tekshiradi"""
        request = self.context.get('request', None) # request bormi
        if request and request.user.is_authenticated:   
            try:
                like = PostLike.objects.get(post=object, author=request.user)  # postga like bosgan foydalanuvchilar ichida request user mavjudmi
                return True
            except PostLike.DoesNotExist:
                return False
        return False
    

class CommentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField('get_replies')
    me_liked = serializers.SerializerMethodField('get_me_liked')
    likes_count = serializers.SerializerMethodField('get_likes_count')

    class Meta:
        model = PostComment
        fields = ("id", "author", "comment", "post", "parent", "created_time", "replies", "me_liked", "likes_count")

    def get_replies(self, object):
        if object.child.exists():
            serializers = self.__class__(object.child.all(), many=True, context=self.context)
            return serializers.data
        else:
            return None
        
    def get_me_liked(self, object):
        user = self.context.get('request').user
        if user.is_authenticated:
            return object.likes.filter(author=user).exists()
        else:
            return False
        
    def get_likes_count(self, object):
        return object.likes.count()
    

class CommentLikeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = CommentLike
        fields = [
            'id',
            'author',
            'comment'
        ]


class PostLikeSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = PostLike
        fields = [
            'id',
            'author',
            'post'
            ]