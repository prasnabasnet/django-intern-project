from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
import requests
import os

from .models import Category, Expense
from .serializers import CategorySerializer, ExpenseSerializer
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    try:
        username = (request.data.get("username") or "").lower().strip()
        password = (request.data.get("password") or "").strip() 

        if not username or not password:
            return Response(
                {"error": "Username and password are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(username=username, password=password)
        token, _ = Token.objects.get_or_create(user=user)

        return Response({"token": token.key}, status=status.HTTP_201_CREATED)
    
    except Exception as e:
        return Response(
            {"error": "An error occurred during registration.", "details": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    try:
        username = (request.data.get("username") or "").lower().strip() 
        password = (request.data.get("password") or "").strip()
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {"error": "Invalid credentials."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {"error": "An error occurred during login.", "details": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET", "POST"])
def category_list(request):
    if request.method == "GET":
        categories = Category.objects.filter(user=request.user)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    serializer = CategorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def expense_list(request):
    if request.method == "GET":
        expenses = Expense.objects.filter(user=request.user)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            expenses = expenses.filter(date__gte=start_date)
        if end_date:
            expenses = expenses.filter(date__lte=end_date)

        serializer = ExpenseSerializer(expenses, many=True)
        return Response(serializer.data)

    serializer = ExpenseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(user=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PUT", "DELETE"])
def expense_detail(request, pk):
    try:
        expense = Expense.objects.get(pk=pk, user=request.user)
    except Expense.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = ExpenseSerializer(expense)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = ExpenseSerializer(expense, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    expense.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def get_exchange_rates(base_currency):
    try:
        url = f"https://open.er-api.com/v6/latest/{base_currency}"
        response = requests.get(url)
        data = response.json()
        return data["rates"], data["time_last_update_utc"]
    except Exception as e:
        raise Exception(f"Failed to fetch exchange rates: {str(e)}")

@api_view(["GET"])
def expense_summary(request):
    try:
        base_currency = os.getenv("BASE_CURRENCY", "USD")
        rates, as_of = get_exchange_rates(base_currency)

        expenses = Expense.objects.filter(user=request.user).values(
            "category__name", "amount", "currency"
        )

        category_totals = {}
        for expense in expenses:
            cat = expense["category__name"]
            amount = float(expense["amount"])
            currency = expense["currency"]

            if currency != base_currency:
                rate = rates.get(currency, 1)
                amount = amount / rate

            if cat not in category_totals:
                category_totals[cat] = 0
            category_totals[cat] += amount

        result = [
            {"category": cat, "total": round(total, 2)}
            for cat, total in category_totals.items()
        ]

        return Response({
            "base_currency": base_currency,
            "as_of": as_of,
            "categories": result
        })
    
    except Exception as e:
        return Response(
            {"error": "Failed to generate summary.", "details": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    
