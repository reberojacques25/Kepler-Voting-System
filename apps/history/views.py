from django.shortcuts import render, get_object_or_404
from apps.elections.models import Election, ElectionWinner

def guild_history(request):
    elections = Election.objects.filter(
        is_published=True
    ).prefetch_related(
        'winners__candidate',
        'winners__position',
        'winners__achievements'
    ).order_by('-start_at')

    return render(request, 'history/guild_history.html', {
        'elections': elections
    })

def council_detail(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    winners = ElectionWinner.objects.filter(
        election=election
    ).select_related(
        'candidate', 'position'
    ).prefetch_related('achievements')

    return render(request, 'history/council_detail.html', {
        'election': election,
        'winners': winners
    })