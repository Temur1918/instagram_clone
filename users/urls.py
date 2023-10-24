from django.contrib import admin
from django.urls import path
from .views import ChangeUserInformationView, ChangeUserPhotoView, CreateUserView, ForgotPasswordView, LoginView, LogOutView, ResetPasswordView, VerifyAPIView, \
    GetNewVerification, LoginRefreshView

urlpatterns = [
    path('login/', LoginView().as_view(), ),
    path('logout/', LogOutView.as_view(), ),
    path('login/refresh/', LoginRefreshView.as_view(), ),
    path('signup/', CreateUserView.as_view(), ),
    path('verify/', VerifyAPIView.as_view(), ),
    path('new-verify/', GetNewVerification.as_view(), ),
    path('change-user/', ChangeUserInformationView.as_view(), ),
    path('photo-step/', ChangeUserPhotoView.as_view(), ),
    path('forgot-password/', ForgotPasswordView.as_view(), ),
    path('password-reset/', ResetPasswordView.as_view(), ),
]
