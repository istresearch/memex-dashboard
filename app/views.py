import json

from django.http import HttpResponse
from django.shortcuts import render, redirect

def index(request):
    response = {
        'msg': 'Hello, World'
    }
    return render(request, 'app/index.html', response)
