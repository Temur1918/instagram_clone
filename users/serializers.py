from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from rest_framework.generics import get_object_or_404
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken

from shared_app.utility import check_email_or_phone, send_email, send_phone_code, check_user_type
from .models import User, UserConfirmation, VIA_EMAIL, VIA_PHONE, NEW, CODE_VERIFIED, DONE, PHOTO_STEP
from rest_framework import exceptions
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

    
class SignUpSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(SignUpSerializer, self).__init__(*args, **kwargs)
        self.fields['email_phone_number'] = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'auth_type',
            'auth_status'
        )
        extra_kwargs = {
            'auth_type': {'read_only': True, 'required': False},
            'auth_status': {'read_only': True, 'required': False}
        }

    def create(self, validated_data):
        """Ro'yxatdan o'tayotgan user uchun maxsus kod yaratish"""
        user = super(SignUpSerializer, self).create(validated_data)
        if user.auth_type == VIA_EMAIL:
            code = user.create_verify_code(VIA_EMAIL)
            send_email(user.email, code)
        elif user.auth_type == VIA_PHONE:
            code = user.create_verify_code(VIA_PHONE)
            send_email(user.phone_number, code)
            # send_phone_code(user.phone_number, code)
        user.save()
        return user

    def validate(self, data):
        super(SignUpSerializer, self).validate(data)
        data = self.auth_validate(data)
        return data

    @staticmethod
    def auth_validate(data):
        """User tomonidan kiritilgan malumotni validatsiya tekshiruvidan o'tkazish: Funksiyaga uzatilgan malumot(data) ichidan get metodi yordamida user kiritgan qiymat ajratib olinayabdi va u email yoki phone_number tekshirilayabdi
        email bo'lsa userning auty_type atributi qiymati email deb belgilanayabdi, phone_number bo'lsa phone_number deb: Agar email yoki phone_number bo'lmasa ValidationError xatoligi qaytariladi"""
        print(data)
        user_input = str(data.get('email_phone_number')).lower()
        input_type = check_email_or_phone(user_input) # email or phone
        if input_type == "email":
            data = {
                "email": user_input,
                "auth_type": VIA_EMAIL
            }
        elif input_type == "phone":
            data = {
                "phone_number": user_input,
                "auth_type": VIA_PHONE
            }
        else:
            data = {
                'success': False,
                'message': "You must send email or phone number"
            }
            raise ValidationError(data)

        return data

    def validate_email_phone_number(self, value):
        """Bu validatsiya funksiyasi vazifasi signup qilayotgan foydalanuvchi email yoki telefon raqami bazada mavjud yoki mavjud emasligini tekshiradi mavjud bo'lsa agar ValidationError xatolik qaytaradi"""
        value = value.lower()
        if value and User.objects.filter(email=value).exists():
            data = {
                "success": False,
                "message": "Bu email allaqachon ma'lumotlar bazasida bor"
            }
            raise ValidationError(data)
        elif value and User.objects.filter(phone_number=value).exists():
            data = {
                "success": False,
                "message": "Bu telefon raqami allaqachon ma'lumotlar bazasida bor"
            }
            raise ValidationError(data)

        return value

    def to_representation(self, instance):
        data = super(SignUpSerializer, self).to_representation(instance)
        data.update(instance.token())

        return data


class ChangeUserInformation(serializers.Serializer):
    """User malumotlarini tahrirlash uchun."""
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(seld, data):
        """validatsiya maqsadi ikkala parol bir xilligini tekshirish!"""
        password = data.get('password', None)
        confirm_password = data.get('confirm_password', None)
        if password != confirm_password:
            raise ValidationError(
                {
                    "message": "Ikkala maydondagi parol bir xil bo'lishi kerak"
                }
            )     
        if password:
            """Agar parol mavjud bo'lsa djangoning validate_password metodi orqali validatsiya qilamiz."""
            validate_password(password)
            validate_password(confirm_password)

        return data
    
    def validate_username(self, username):
        """username uchun validatsiya"""
        if len(username) < 5 or len (username) > 30:
            raise ValidationError(
                {
                    "message": "Usernameingiz uzunligi 5 ta belgidan katta va 30 ta belgidan kichik bo'lishiga etibor bering!"
                }
            )
        if username.isdigit():
            raise ValidationError(
                {
                    "message": "Usernamingiz to'liq raqamlardan iborat bo'lishi mumkin emas!"
                }
            )
        
        return username
        
    def update(self, instance, validated_data):
        """Foydalanuvchi tomonidan kiritlgan malumotlarni obyekt sifatida qabul qilib agar malumotlar validatsiyadan o'tsa user malumotlarini o'zgartirib yangi obyeky qaytaradi!"""
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)
        instance.password = validated_data.get('password', instance.password)
        if validated_data.get('password'):
            instance.set_password(validated_data.get('password'))
        if instance.aut_status == CODE_VERIFIED:
            instance.aut_status = DONE
        instance.save()
        return instance
    


class ChangeUserPhotoSerializer(serializers.Serializer):
    """User profil rasmini yangilash to'g'rirog'i qo'yish
    bunda atribut yaratilib allowed_extensions yordamida kerakli formatlar tanlab olindi
    update metodi yordamida rasm agar mavjud bo'lsa status o'zgartirilib yangi obyektga photo qiymatini 
    kiritib obyektni saqlab shu obyektni qaytardik"""
    photo = serializers.ImageField(validators=[FileExtensionValidator(allowed_extensions=[
        'jpg', 'jpeg', 'png', 'heic', 'heif'
    ])])

    def update(self, instance, validated_data):
        photo = validated_data.get('photo')
        if photo:
            instance.photo = photo
            instance.auth_status = PHOTO_STEP
            instance.save()
        return instance
    


class LoginSerializer(TokenObtainPairSerializer):
    """Login Serializer"""
    def __init__(self, *args, **kwargs):
        """Ushbu funksiya konstruktor vazifasini bajaradi! va u serializerga 2 ta maydon qo'shyabdi
        ikkala maydon to'ldirilishi majburiy(required=True)"""
        super(LoginSerializer, self).__init__(*args, **kwargs)
        self.fields['userinput'] = serializers.CharField(required=True)
        self.fields['username'] = serializers.CharField(required=True, read_only=True)

    def auth_validate(self, data):
        """Ushbu validatsiya funksiyasi 1 - vazifasi user kiritayotgan malumot turini aniqlab
        (username, email, phone_number) usernamenini olish!"""
        user_input = data.get('user_input')
        if check_user_type(user_input) == 'username':
            username = user_input
        elif check_user_type(user_input) == 'email':
            user = self.get_user(email__iexect=user_input)  # ushbu email tegishli bo'lgan foydalanuvchini olish
            username = user.username
        elif check_user_type(user_input) == 'phone':
            user = self.get_user(phone_number=user_input) # ushbu telefon raqam tegishli bo'lgan goydalanuvchini olish
            username = user.username
        else: 
            data = {
                'success': True,
                'message': "Siz email, username yoki telefon raqamingizni kiritishingiz kerak!"
            }
            raise ValidationError(data)
        
        authentication_kwargs = {
            # bu dictionary vazifasi username va parolni taminlash
            self.username_field: username,
            'password': data['password']
        }

        current_user = User.objects.filter(username__iexact=username).first()  # Mavjud username oqali foydalanuvchini olish : username__iexact vazifasi katta kichik harflarni etiborga olmaslik :: .first() birinchi uchragan userni olish uchun


        """Agar user mavjud bo'lmasa va user statusi NEW yoki CODE_VERIFIED bo'lsa foydalanuvchi login qila olmaydi shu uchun xatolikni qayataramiz!"""
        if current_user is not None and current_user.auth_status in [NEW, CODE_VERIFIED]:
            raise ValidationError(
                {
                    'success': False,
                    'message': 'Siz ro\'yxatdan to\'liq o\'tmagansiz!' 
                }
            )
        
        user = authenticate(**authentication_kwargs) # bu funksiya username va parol to'g'riligini tekshirib autentificatsiya jarayonini boshqaradi

        if user is not None:
            self.user = user
        else:
            raise ValidationError(
                {
                    'success': False,
                    'message': "Kechirasiz login yoki parolingiz noto'g'ri. Qaytadan o'rinib ko'ring!"
                }
            )
        
    def validate(self, data):
        """Ushbu validate funsiyasi user statusini tekshiradi u DONE, PHOTO_STEP bo'lmasa True aks holda xatolik qaytaradi!"""
        self.auth_validate(data)
        if self.user.aut_status not in [DONE, PHOTO_STEP]:
            raise PermissionDenied("Siz login qila olmaysiz. Avval ro'yxatdan to'liq o'tib keyin qayta o'rinib ko'ring!")
        data = self.user.token()   # foydalanuvchi tokenini olish
        data['auth_status'] = self.user.auth_status
        # data['full_name'] = self.user.full_name
        return data
    
    def get_user(self, **kwargs):
        """Foydalanuvchini qidirish agar topilmasa xatolik qaytaradi!"""
        users = User.objects.filter(**kwargs)
        if not users.exists():
            raise ValidationError(
                {
                    'message': "Account topilmadi, Login to'g'riligiga etibor berib qaytadan o'rinib ko'ring!"
                }
            )
        return users.first()
    

class LoginRefreshSerializer(TokenRefreshSerializer):
    """Kodning asosiy vazifasi foydalanuvchining tokenini yangilash va foydalanuvchining oxirgi kirish vaqti ma'lumotlarini yangilashdir."""
    def validate(self, attrs):
        data = super().validate(attrs)
        """TokenRefreshSerializer sinfidan validate metodini chaqiradi va malumotlarni data o'zgaruvchisiga o'zlashtiradi!"""
        access_token_instance = AccessToken(data['access'])
        user_id = access_token_instance['user_id']
        user = get_object_or_404(User, id=user_id)
        update_last_login(None, user)
        return data
    

class LogOutSerializer(serializers.Serializer):
    """Log Out qilish uchun refresh maydoni esa buning uchun token kkligini aytyabdi"""
    refresh = serializers.CharField()   


class ForgotPasswordSerializer(serializers.Serializer):
    """Bitta maydon qo'shildi kiritish majburiy validate funksiyasida qiymat mavjud bo'lsa olinadi"""
    email_or_phone = serializers.CharField(write_only=True, required=True)

    def validate(seld, attrs):
        email_or_phone = attrs.get('email_or_phone', None)
        if email_or_phone is None:
            raise ValidationError(
                {
                    'success': False,
                    'message': "Email yoki telefon raqami kiritilishi shart!"
                }
            )
        user = user.objects.filter(Q(phone_number=email_or_phone) | Q(email=email_or_phone))  # Bazaga so'rov yuborilyabdi email yoki telefon raqam birortasiga teng bo'lsa olinadi!
        if not user.exists():
            raise NotFound(detail="Foydalanuvchi topilmadi!")
        attrs['user'] = user.first()
        return attrs
    

class ResetPasswordSerializer(serializers.ModelSerializer):
    """Kodning vazifasi foydalanuvchining parolini tiklash va yangilash imkoniyatini berishdir."""
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(min_length=8, required=True, write_only=True)
    confirm_password = serializers.CharField(min_length=8, required=True, write_only=True)

    class Meta: 
        model = User
        fields = (
            'id',
            'password',
            'confirm_password'
        )

    def validate(self, data):
        password = data.get('password', None)
        confirm_password = data.get('confirm_password', None)
        if password != confirm_password:
            raise ValidationError(
                {
                    'success': False,
                    'message': "Ikkala maydondagi parollar qiymati bir-biriga teng bo'lishi kerak!"
                }
            )
        if password:
            validate_password(password)
        return data
    
    def update(self, instance, validated_data):
        """Kiritilgan yangi parolni olib set_password metodi yordamida obyektga yozamiz"""
        password = validated_data.pop('password')
        instance.set_password(password)
        return super(ResetPasswordSerializer, self).update(instance, validated_data) # ModelSerializer classining update metodi chaqirilib yangilangan malumot yuborilmoqda

    

    