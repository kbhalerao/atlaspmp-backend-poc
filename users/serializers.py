from django.contrib.auth import get_user_model
from rest_framework import serializers


class CustomUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)

    class Meta:
        model = get_user_model()
        fields = [
            'id', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'password'
        ]
        read_only_fields = ('id', 'date_joined')

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = self.Meta.model(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
