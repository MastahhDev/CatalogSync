from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'home.html')

def featured(request):
    return render(request, 'featured.html')

def ps4(request):
    return render(request, 'ps4.html')

def ps5(request):
    return render(request, 'ps5.html')

def questions(request):
    return render(request, 'questions.html')

def about(request):
    return render(request, 'about.html')