from schedule.models import Court
def locked_courts(request):
    locked_num_courts = request.session.get('locked_num_courts')
    if locked_num_courts:
        courts = Court.objects.all().order_by('id')[:int(locked_num_courts)]
    else:
        courts = []
    return {
        'locked_num_courts': locked_num_courts,
        'locked_courts': courts,
    }