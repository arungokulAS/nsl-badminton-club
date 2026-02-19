from django.shortcuts import render

def public_referee(request):
    return render(request, 'core/public_referee.html')

def public_contact(request):
    return render(request, 'core/public_contact.html')

def print_menu(request):
    return render(request, 'core/print_menu.html')
