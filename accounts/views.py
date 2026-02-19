import os
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_protect

@csrf_protect
def admin_login(request):
	error = None
	if request.method == 'POST':
		password = request.POST.get('password')
		admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
		if password == admin_password:
			request.session['is_admin'] = True
			return redirect('/admin/dashboard')
		else:
			error = 'Invalid password.'
	return render(request, 'accounts/admin_login.html', {'error': error})

def admin_logout(request):
	request.session.flush()
	return redirect('/admin/login')

def admin_dashboard(request):
	if not request.session.get('is_admin'):
		return redirect('/admin/login')
	return render(request, 'accounts/admin_dashboard.html')
