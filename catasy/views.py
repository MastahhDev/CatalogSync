from django.shortcuts import redirect

def redirect_to_featured(request):
    return redirect('/featured')