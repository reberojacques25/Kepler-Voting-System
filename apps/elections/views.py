from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import (
    Election, Position, Candidate, Vote,
    PositionApplication, ApplicationField, ApplicationAnswer,
    CampaignPost
)
from .permissions import verified_and_allowed_required


def elections_list(request):
    elections = Election.objects.filter(is_published=True).order_by('-start_at')
    if request.user.is_authenticated and not request.user.is_staff:
        visible_ids = [e.id for e in elections if e.student_can_see(request.user)]
        elections = elections.filter(id__in=visible_ids)
    return render(request, 'elections/elections_list.html', {'elections': elections})


def election_detail(request, election_id):
    election = get_object_or_404(Election, id=election_id, is_published=True)
    if request.user.is_authenticated and not request.user.is_staff:
        if not election.student_can_see(request.user):
            messages.error(request, 'You do not have access to this election.')
            return redirect('elections:elections_list')
    positions_with_eligibility = []
    for position in election.positions.all():
        can_vote = False
        already_voted = False
        if request.user.is_authenticated:
            already_voted = Vote.objects.filter(
                voter=request.user, election=election, position=position
            ).exists()
            can_vote = _student_can_vote_position(request.user, election, position)
        positions_with_eligibility.append({
            'position': position,
            'can_vote': can_vote,
            'already_voted': already_voted,
        })
    return render(request, 'elections/election_detail.html', {
        'election': election,
        'positions_with_eligibility': positions_with_eligibility,
    })


def _student_can_vote_position(user, election, position):
    if not user.is_email_verified:
        return False
    if not user.can_vote:
        return False
    if election.voting_scope == 'cohort':
        if not user.cohort:
            return False
        if not user.is_cohort_confirmed:
            return False
        if not election.student_can_vote(user):
            return False
    if position.voting_scope == 'cohort':
        if not user.cohort:
            return False
        if not user.is_cohort_confirmed:
            return False
        if not position.student_can_vote(user):
            return False
    return True


def _student_can_apply_position(user, election, position):
    if election.voting_scope == 'cohort':
        if not user.cohort:
            return False, 'You have no cohort assigned. Contact admin.'
        if not user.is_cohort_confirmed:
            return False, 'Your cohort has not been confirmed by admin yet.'
        if not election.student_can_vote(user):
            cohorts = ', '.join(election.voting_cohorts.values_list('name', flat=True))
            return False, f'This election is restricted to: {cohorts}.'
    if position.voting_scope == 'cohort':
        if not user.cohort:
            return False, 'You have no cohort assigned. Contact admin.'
        if not user.is_cohort_confirmed:
            return False, 'Your cohort has not been confirmed by admin yet.'
        if not position.student_can_vote(user):
            cohorts = ', '.join(position.allowed_cohorts.values_list('name', flat=True))
            return False, f'This position is restricted to: {cohorts}.'
    return True, None


@verified_and_allowed_required
def vote_position(request, election_id, position_id):
    election = get_object_or_404(Election, id=election_id, is_published=True)
    position = get_object_or_404(Position, id=position_id, election=election)
    if not election.is_open:
        messages.error(request, 'Voting is not open for this election.')
        return redirect('elections:election_detail', election_id=election.id)
    if not election.student_can_see(request.user):
        messages.error(request, 'You do not have access to this election.')
        return redirect('elections:elections_list')
    if not _student_can_vote_position(request.user, election, position):
        if not request.user.cohort:
            messages.error(request, 'You have no cohort assigned. Contact admin.')
        elif not request.user.is_cohort_confirmed:
            messages.error(request, 'Your cohort has not been confirmed by admin yet.')
        else:
            messages.error(request, 'You are not eligible to vote on this position.')
        return redirect('elections:election_detail', election_id=election.id)
    if Vote.objects.filter(voter=request.user, election=election, position=position).exists():
        messages.info(request, f'You already voted for {position.title}.')
        return redirect('elections:election_detail', election_id=election.id)
    candidates = Candidate.objects.filter(
        election=election, position=position, status='approved'
    ).order_by('full_name')
    if not candidates.exists():
        messages.warning(request, 'No approved candidates available for this position yet.')
        return redirect('elections:election_detail', election_id=election.id)
    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id')
        candidate = get_object_or_404(
            Candidate, id=candidate_id, election=election, position=position, status='approved'
        )
        Vote.objects.create(voter=request.user, election=election, position=position, candidate=candidate)
        messages.success(request, f'Vote recorded for {position.title}. Thank you!')
        return redirect('elections:election_detail', election_id=election.id)
    return render(request, 'elections/vote_position.html', {
        'election': election, 'position': position, 'candidates': candidates,
    })


def results(request, election_id):
    election = get_object_or_404(Election, id=election_id, is_published=True)
    if request.user.is_authenticated and not request.user.is_staff:
        if not election.student_can_see(request.user):
            messages.error(request, 'You do not have access to this election.')
            return redirect('elections:elections_list')
    if not election.is_closed and not election.allow_live_results:
        messages.info(request, 'Results will be available after voting closes.')
        return redirect('elections:election_detail', election_id=election.id)
    data = []
    for pos in election.positions.all():
        qs = (Vote.objects.filter(election=election, position=pos)
              .values('candidate__id', 'candidate__full_name')
              .annotate(votes=Count('id')).order_by('-votes'))
        total = sum(r['votes'] for r in qs) or 0
        rows = []
        for r in qs:
            pct = (r['votes'] / total * 100) if total else 0
            rows.append({
                'candidate_id': r['candidate__id'],
                'candidate': r['candidate__full_name'],
                'votes': r['votes'],
                'pct': round(pct, 2),
            })
        data.append({'position': pos, 'total': total, 'rows': rows})
    turnout_total_votes = Vote.objects.filter(election=election).count()
    return render(request, 'elections/results.html', {
        'election': election, 'data': data, 'turnout_votes': turnout_total_votes,
    })


def live_results_json(request, election_id):
    election = get_object_or_404(Election, id=election_id, is_published=True)
    if not election.allow_live_results and not election.is_closed:
        return JsonResponse({'detail': 'Live results disabled.'}, status=403)
    payload = {'election': election.name, 'updated_at': timezone.now().isoformat(), 'positions': []}
    for pos in election.positions.all():
        qs = (Vote.objects.filter(election=election, position=pos)
              .values('candidate__full_name').annotate(votes=Count('id')).order_by('-votes'))
        total = sum(r['votes'] for r in qs) or 0
        payload['positions'].append({
            'position': pos.title, 'total': total,
            'results': [{'candidate': r['candidate__full_name'], 'votes': r['votes']} for r in qs],
        })
    return JsonResponse(payload)


# ── Student Applications ───────────────────────────────────────────────────────

@login_required
def open_positions(request):
    elections = Election.objects.filter(is_published=True).prefetch_related('positions').order_by('-start_at')
    elections_with_positions = []
    for election in elections:
        positions = election.positions.filter(applications_open=True)
        if not positions.exists():
            continue
        positions_data = []
        for position in positions:
            existing = PositionApplication.objects.filter(position=position, applicant=request.user).first()
            can_apply, restriction_reason = _student_can_apply_position(request.user, election, position)
            positions_data.append({
                'position': position,
                'application': existing,
                'can_apply': can_apply,
                'restriction_reason': restriction_reason,
            })
        elections_with_positions.append({'election': election, 'positions': positions_data})
    return render(request, 'elections/open_positions.html', {'elections_with_positions': elections_with_positions})


@login_required
def apply_position(request, election_id, position_id):
    election = get_object_or_404(Election, id=election_id, is_published=True)
    position = get_object_or_404(Position, id=position_id, election=election, applications_open=True)
    can_apply, restriction_reason = _student_can_apply_position(request.user, election, position)
    if not can_apply:
        messages.error(request, restriction_reason)
        return redirect('elections:open_positions')
    existing = PositionApplication.objects.filter(position=position, applicant=request.user).first()
    if existing:
        messages.info(request, f'You already applied for {position.title}. Your application is {existing.get_status_display()}.')
        return redirect('elections:open_positions')
    fields = ApplicationField.objects.filter(position=position).order_by('order')
    if request.method == 'POST':
        slogan = request.POST.get('slogan', '').strip()
        photo = request.FILES.get('photo')
        errors = []
        for field in fields:
            if field.field_type == 'file':
                value = request.FILES.get(f'field_{field.id}')
            else:
                value = request.POST.get(f'field_{field.id}', '').strip()
            if field.is_required and not value:
                errors.append(f'"{field.label}" is required.')
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            application = PositionApplication.objects.create(
                position=position, applicant=request.user,
                why_running='via custom fields', manifesto='via custom fields',
                slogan=slogan, photo=photo,
            )
            for field in fields:
                if field.field_type == 'file':
                    file_value = request.FILES.get(f'field_{field.id}')
                    ApplicationAnswer.objects.create(application=application, field=field, file=file_value)
                else:
                    text_value = request.POST.get(f'field_{field.id}', '').strip()
                    ApplicationAnswer.objects.create(application=application, field=field, value=text_value)
            messages.success(request, f'Application submitted for {position.title}. Admin will review it shortly.')
            return redirect('elections:my_applications')
    return render(request, 'elections/apply_position.html', {'election': election, 'position': position, 'fields': fields})


@login_required
def my_applications(request):
    applications = PositionApplication.objects.filter(
        applicant=request.user
    ).select_related('position', 'position__election').order_by('-applied_at')
    return render(request, 'elections/my_applications.html', {'applications': applications})


# ── Campaign Posts ─────────────────────────────────────────────────────────────

def campaign_browse(request, election_id):
    election = get_object_or_404(Election, id=election_id, is_published=True)
    candidates = Candidate.objects.filter(
        election=election, status='approved'
    ).prefetch_related('campaign_posts').select_related('position', 'student').order_by('position__order', 'full_name')
    positions_data = []
    for position in election.positions.all():
        position_candidates = [c for c in candidates if c.position_id == position.id]
        if position_candidates:
            positions_data.append({'position': position, 'candidates': position_candidates})
    return render(request, 'elections/campaign_browse.html', {'election': election, 'positions_data': positions_data})


def candidate_profile(request, candidate_id):
    candidate = get_object_or_404(
        Candidate.objects.select_related('position', 'position__election', 'student').prefetch_related('campaign_posts'),
        id=candidate_id, status='approved'
    )
    approved_posts = candidate.campaign_posts.filter(status='approved')
    return render(request, 'elections/candidate_profile.html', {'candidate': candidate, 'posts': approved_posts})


@login_required
def my_campaign(request):
    candidacies = Candidate.objects.filter(
        student=request.user, status='approved'
    ).select_related('position', 'election').prefetch_related('campaign_posts')
    if not candidacies.exists():
        messages.info(request, 'You are not an approved candidate in any election yet.')
        return redirect('elections:my_applications')
    return render(request, 'elections/my_campaign.html', {'candidacies': candidacies})


@login_required
def campaign_post_create(request, candidate_id):
    candidate = get_object_or_404(Candidate, id=candidate_id, student=request.user, status='approved')
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        link = request.POST.get('link', '').strip()
        image = request.FILES.get('image')
        if not title:
            messages.error(request, 'Post title is required.')
        else:
            CampaignPost.objects.create(
                candidate=candidate, title=title, content=content,
                link=link, image=image, status='pending',
            )
            messages.success(request, 'Campaign post submitted for admin approval.')
            return redirect('elections:my_campaign')
    return render(request, 'elections/campaign_post_form.html', {'candidate': candidate})


@login_required
def campaign_post_delete(request, post_id):
    post = get_object_or_404(CampaignPost, id=post_id, candidate__student=request.user)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted.')
    return redirect('elections:my_campaign')