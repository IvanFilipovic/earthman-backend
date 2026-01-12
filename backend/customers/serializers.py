from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Customer


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = Customer
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'newsletter')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'newsletter': {'required': False}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')

        customer = Customer.objects.create_user(
            password=password,
            **validated_data
        )
        return customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('id', 'email', 'first_name', 'last_name', 'newsletter', 'is_active', 'date_joined')
        read_only_fields = ('id', 'date_joined')
