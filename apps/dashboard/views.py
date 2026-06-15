import csv
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.elections.models import (
    Election, Vote, Position, Candidate,
    PositionApplication, ApplicationField,
    ElectionWinner, Achievement, CampaignPost
)
from apps.accounts.models import User, Cohort
from .permissions import staff_required


@login_required
def student(request):
    if request.user.is_staff:
        return redirect('dashboard:admin_overview')
    elections = Election.objects.filter(is_published=True).order_by('-start_at')
    my_votes = Vote.objects.filter(voter=request.user).select_related(
        'election', 'position', 'candidate'
    )
    voted_map = {}
    for v in my_votes:
        voted_map.setdefault(v.election_id, set()).add(v.position_id)
    return render(request, 'dashboard/student.html', {
        'elections': elections,
        'my_votes': my_votes,
        'voted_map': voted_map,
    })


@staff_required
def admin_overview(request):
    students_total = User.objects.count()
    students_verified = User.objects.filter(is_email_verified=True, is_active=True).count()
    students_blocked = User.objects.filter(can_vote=False).count()
    elections_total = Election.objects.count()
    votes_total = Vote.objects.count()
    elections = Election.objects.all().order_by('-start_at')
    summaries = []
    for e in elections:
        votes = Vote.objects.filter(election=e).count()
        summaries.append({
            'election': e,
            'votes': votes,
            'open': e.is_open,
            'closed': e.is_closed,
        })
    pending_cohort_students = User.objects.filter(
        is_staff=False,
        cohort__isnull=False,
        is_cohort_confirmed=False
    )
    return render(request, 'dashboard/admin_overview.html', {
        'students_total': students_total,
        'students_verified': students_verified,
        'students_blocked': students_blocked,
        'elections_total': elections_total,
        'votes_total': votes_total,
        'summaries': summaries,
        'pending_cohort_students': pending_cohort_students,
    })


@staff_required
def export_election_results_csv(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    rows = (Vote.objects
            .filter(election=election)
            .values('position__title', 'candidate__full_name')
            .annotate(votes=Count('id'))
            .order_by('position__title', '-votes'))
    resp = HttpResponse(content_type='text/csv')
    resp['Content-Disposition'] = f'attachment; filename="{election.name}-results.csv"'
    writer = csv.writer(resp)
    writer.writerow(['Election', 'Position', 'Candidate', 'Votes'])
    for r in rows:
        writer.writerow([election.name, r['position__title'], r['candidate__full_name'], r['votes']])
    return resp


# ── Students ──────────────────────────────────────────────────────────────────

@staff_required
def admin_students(request):
    students = User.objects.filter(is_staff=False).select_related('cohort').order_by('-date_joined')
    cohorts = Cohort.objects.all()
    cohort_id = request.GET.get('cohort')
    if cohort_id:
        students = students.filter(cohort_id=cohort_id)
    status = request.GET.get('status')
    if status == 'verified':
        students = students.filter(is_email_verified=True)
    elif status == 'unverified':
        students = students.filter(is_email_verified=False)
    elif status == 'blocked':
        students = students.filter(can_vote=False)
    return render(request, 'dashboard/admin_students.html', {
        'students': students,
        'cohorts': cohorts,
        'total': students.count(),
        'selected_cohort': cohort_id,
        'selected_status': status,
    })


@staff_required
def admin_toggle_student(request, student_id):
    if request.method == 'POST':
        student = get_object_or_404(User, id=student_id, is_staff=False)
        action = request.POST.get('action')
        if action == 'block':
            student.can_vote = False
            student.save()
        elif action == 'unblock':
            student.can_vote = True
            student.save()
        elif action == 'verify':
            student.is_email_verified = True
            student.save()
        elif action == 'confirm_cohort':
            student.is_cohort_confirmed = True
            student.save()
        elif action == 'unconfirm_cohort':
            student.is_cohort_confirmed = False
            student.save()
    return JsonResponse({'ok': True})


# ── Cohorts ───────────────────────────────────────────────────────────────────

@staff_required
def admin_cohorts(request):
    cohorts = Cohort.objects.annotate(student_count=Count('students')).order_by('-year')
    return render(request, 'dashboard/admin_cohorts.html', {'cohorts': cohorts})


@staff_required
def admin_cohort_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        year = request.POST.get('year')
        Cohort.objects.create(name=name, year=year)
        messages.success(request, f'Cohort "{name}" created.')
        return redirect('dashboard:admin_cohorts')
    return render(request, 'dashboard/admin_cohort_form.html', {'action': 'Add', 'cohort': None})


@staff_required
def admin_cohort_edit(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id)
    if request.method == 'POST':
        cohort.name = request.POST.get('name')
        cohort.year = request.POST.get('year')
        cohort.save()
        messages.success(request, f'Cohort "{cohort.name}" updated.')
        return redirect('dashboard:admin_cohorts')
    return render(request, 'dashboard/admin_cohort_form.html', {'action': 'Edit', 'cohort': cohort})


@staff_required
def admin_cohort_delete(request, cohort_id):
    cohort = get_object_or_404(Cohort, id=cohort_id)
    if request.method == 'POST':
        cohort.delete()
        messages.success(request, 'Cohort deleted.')
    return redirect('dashboard:admin_cohorts')


# ── Elections ─────────────────────────────────────────────────────────────────

@staff_required
def admin_elections(request):
    elections = Election.objects.all().order_by('-start_at')
    return render(request, 'dashboard/admin_elections.html', {'elections': elections})


@staff_required
def admin_election_create(request):
    cohorts = Cohort.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        start_at = request.POST.get('start_at')
        end_at = request.POST.get('end_at')
        is_published = request.POST.get('is_published') == 'on'
        allow_live_results = request.POST.get('allow_live_results') == 'on'
        visibility_scope = request.POST.get('visibility_scope', 'all')
        voting_scope = request.POST.get('voting_scope', 'all')
        visible_cohort_ids = request.POST.getlist('visible_to_cohorts')
        voting_cohort_ids = request.POST.getlist('voting_cohorts')
        election = Election.objects.create(
            name=name, description=description,
            start_at=start_at, end_at=end_at,
            is_published=is_published, allow_live_results=allow_live_results,
            visibility_scope=visibility_scope, voting_scope=voting_scope,
        )
        if visible_cohort_ids:
            election.visible_to_cohorts.set(visible_cohort_ids)
        if voting_cohort_ids:
            election.voting_cohorts.set(voting_cohort_ids)
        messages.success(request, 'Election created successfully.')
        return redirect('dashboard:admin_election_manage', election_id=election.id)
    return render(request, 'dashboard/admin_election_form.html', {
        'action': 'Create', 'election': None, 'cohorts': cohorts,
    })


@staff_required
def admin_election_edit(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    cohorts = Cohort.objects.all()
    if request.method == 'POST':
        election.name = request.POST.get('name')
        election.description = request.POST.get('description', '')
        election.start_at = request.POST.get('start_at')
        election.end_at = request.POST.get('end_at')
        election.is_published = request.POST.get('is_published') == 'on'
        election.allow_live_results = request.POST.get('allow_live_results') == 'on'
        election.visibility_scope = request.POST.get('visibility_scope', 'all')
        election.voting_scope = request.POST.get('voting_scope', 'all')
        visible_cohort_ids = request.POST.getlist('visible_to_cohorts')
        voting_cohort_ids = request.POST.getlist('voting_cohorts')
        election.save()
        election.visible_to_cohorts.set(visible_cohort_ids)
        election.voting_cohorts.set(voting_cohort_ids)
        messages.success(request, 'Election updated successfully.')
        return redirect('dashboard:admin_elections')
    return render(request, 'dashboard/admin_election_form.html', {
        'action': 'Edit', 'election': election, 'cohorts': cohorts,
    })


@staff_required
def admin_election_delete(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    if request.method == 'POST':
        election.delete()
        messages.success(request, 'Election deleted.')
    return redirect('dashboard:admin_elections')


@staff_required
def admin_election_manage(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    positions = Position.objects.filter(
        election=election
    ).prefetch_related('allowed_cohorts', 'application_fields').order_by('order', 'title')
    cohorts = Cohort.objects.all()
    return render(request, 'dashboard/admin_election_manage.html', {
        'election': election, 'positions': positions, 'cohorts': cohorts,
    })


# ── Positions ─────────────────────────────────────────────────────────────────

@staff_required
def admin_position_create(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    cohorts = Cohort.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        order = request.POST.get('order', 0)
        voting_scope = request.POST.get('voting_scope', 'all')
        applications_open = request.POST.get('applications_open') == 'on'
        allowed_cohort_ids = request.POST.getlist('allowed_cohorts')
        position = Position.objects.create(
            election=election, title=title, description=description,
            order=order, voting_scope=voting_scope, applications_open=applications_open,
        )
        if allowed_cohort_ids:
            position.allowed_cohorts.set(allowed_cohort_ids)
        messages.success(request, f'Position "{title}" created.')
        return redirect('dashboard:admin_election_manage', election_id=election.id)
    return render(request, 'dashboard/admin_position_form.html', {
        'election': election, 'position': None, 'cohorts': cohorts, 'action': 'Add',
    })


@staff_required
def admin_position_edit(request, election_id, position_id):
    election = get_object_or_404(Election, id=election_id)
    position = get_object_or_404(Position, id=position_id, election=election)
    cohorts = Cohort.objects.all()
    if request.method == 'POST':
        position.title = request.POST.get('title')
        position.description = request.POST.get('description', '')
        position.order = request.POST.get('order', 0)
        position.voting_scope = request.POST.get('voting_scope', 'all')
        position.applications_open = request.POST.get('applications_open') == 'on'
        allowed_cohort_ids = request.POST.getlist('allowed_cohorts')
        position.save()
        position.allowed_cohorts.set(allowed_cohort_ids)
        messages.success(request, f'Position "{position.title}" updated.')
        return redirect('dashboard:admin_election_manage', election_id=election.id)
    return render(request, 'dashboard/admin_position_form.html', {
        'election': election, 'position': position, 'cohorts': cohorts, 'action': 'Edit',
    })


@staff_required
def admin_position_delete(request, election_id, position_id):
    position = get_object_or_404(Position, id=position_id, election_id=election_id)
    if request.method == 'POST':
        position.delete()
        messages.success(request, 'Position deleted.')
    return redirect('dashboard:admin_election_manage', election_id=election_id)


@staff_required
def admin_position_toggle_applications(request, election_id, position_id):
    position = get_object_or_404(Position, id=position_id, election_id=election_id)
    if request.method == 'POST':
        position.applications_open = not position.applications_open
        position.save()
    return JsonResponse({'applications_open': position.applications_open})


# ── Application Fields ────────────────────────────────────────────────────────

@staff_required
def admin_position_fields(request, election_id, position_id):
    election = get_object_or_404(Election, id=election_id)
    position = get_object_or_404(Position, id=position_id, election=election)
    fields = ApplicationField.objects.filter(position=position).order_by('order')
    return render(request, 'dashboard/admin_position_fields.html', {
        'election': election, 'position': position, 'fields': fields,
    })


@staff_required
def admin_field_create(request, election_id, position_id):
    election = get_object_or_404(Election, id=election_id)
    position = get_object_or_404(Position, id=position_id, election=election)
    if request.method == 'POST':
        label = request.POST.get('label')
        field_type = request.POST.get('field_type', 'textarea')
        is_required = request.POST.get('is_required') == 'on'
        help_text = request.POST.get('help_text', '')
        order = request.POST.get('order', 0)
        ApplicationField.objects.create(
            position=position, label=label, field_type=field_type,
            is_required=is_required, help_text=help_text, order=order,
        )
        messages.success(request, f'Field "{label}" added.')
        return redirect('dashboard:admin_position_fields', election_id=election_id, position_id=position_id)
    return render(request, 'dashboard/admin_field_form.html', {
        'election': election, 'position': position, 'field': None, 'action': 'Add',
    })


@staff_required
def admin_field_edit(request, election_id, position_id, field_id):
    election = get_object_or_404(Election, id=election_id)
    position = get_object_or_404(Position, id=position_id, election=election)
    field = get_object_or_404(ApplicationField, id=field_id, position=position)
    if request.method == 'POST':
        field.label = request.POST.get('label')
        field.field_type = request.POST.get('field_type', 'textarea')
        field.is_required = request.POST.get('is_required') == 'on'
        field.help_text = request.POST.get('help_text', '')
        field.order = request.POST.get('order', 0)
        field.save()
        messages.success(request, f'Field "{field.label}" updated.')
        return redirect('dashboard:admin_position_fields', election_id=election_id, position_id=position_id)
    return render(request, 'dashboard/admin_field_form.html', {
        'election': election, 'position': position, 'field': field, 'action': 'Edit',
    })


@staff_required
def admin_field_delete(request, election_id, position_id, field_id):
    field = get_object_or_404(ApplicationField, id=field_id, position_id=position_id)
    if request.method == 'POST':
        field.delete()
        messages.success(request, 'Field deleted.')
    return redirect('dashboard:admin_position_fields', election_id=election_id, position_id=position_id)


# ── Candidates ────────────────────────────────────────────────────────────────

@staff_required
def admin_candidates(request):
    applications = PositionApplication.objects.select_related(
        'applicant', 'position', 'position__election'
    ).order_by('-applied_at')
    election_id = request.GET.get('election')
    if election_id:
        applications = applications.filter(position__election_id=election_id)
    status = request.GET.get('status')
    if status:
        applications = applications.filter(status=status)
    elections = Election.objects.all().order_by('-start_at')
    return render(request, 'dashboard/admin_candidates.html', {
        'applications': applications,
        'elections': elections,
        'total': applications.count(),
        'selected_election': election_id,
        'selected_status': status,
    })


@staff_required
def admin_application_detail(request, application_id):
    application = get_object_or_404(
        PositionApplication.objects.select_related(
            'applicant', 'position', 'position__election'
        ).prefetch_related('answers__field'),
        id=application_id
    )
    return render(request, 'dashboard/admin_application_detail.html', {'application': application})


@staff_required
def admin_application_review(request, application_id):
    application = get_object_or_404(PositionApplication, id=application_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve' and application.status == 'pending':
            candidate = Candidate.objects.create(
                election=application.position.election,
                position=application.position,
                student=application.applicant,
                full_name=application.applicant.get_full_name() or str(application.applicant.email),
                slogan=application.slogan,
                manifesto=application.manifesto,
                photo=application.photo,
                status='approved',
            )
            application.status = 'approved'
            application.candidate = candidate
            application.reviewed_at = timezone.now()
            application.reviewed_by = request.user
            application.save()
            messages.success(request, f'{application.applicant.email} approved as candidate for {application.position.title}.')
        elif action == 'reject':
            application.status = 'rejected'
            application.reviewed_at = timezone.now()
            application.reviewed_by = request.user
            application.save()
            messages.success(request, f'Application from {application.applicant.email} rejected.')
    return redirect('dashboard:admin_candidates')


# ── Campaigns ─────────────────────────────────────────────────────────────────

@staff_required
def admin_campaigns(request):
    posts = CampaignPost.objects.select_related(
        'candidate', 'candidate__position', 'candidate__position__election'
    ).order_by('-created_at')
    election_id = request.GET.get('election')
    if election_id:
        posts = posts.filter(candidate__position__election_id=election_id)
    status = request.GET.get('status')
    if status:
        posts = posts.filter(status=status)
    elections = Election.objects.all().order_by('-start_at')
    return render(request, 'dashboard/admin_campaigns.html', {
        'posts': posts,
        'elections': elections,
        'total': posts.count(),
        'selected_election': election_id,
        'selected_status': status,
    })


@staff_required
def admin_campaign_review(request, post_id):
    post = get_object_or_404(CampaignPost, id=post_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            post.status = 'approved'
            post.save()
            messages.success(request, 'Campaign post approved.')
        elif action == 'reject':
            post.status = 'rejected'
            post.save()
            messages.success(request, 'Campaign post rejected.')
    return redirect('dashboard:admin_campaigns')


# ── Declare Winners ───────────────────────────────────────────────────────────

@staff_required
def admin_declare_winners(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    positions = Position.objects.filter(election=election).prefetch_related('candidates', 'winners')
    positions_data = []
    for position in positions:
        candidates = Candidate.objects.filter(
            position=position, status='approved'
        ).annotate(vote_count=Count('votes')).order_by('-vote_count')
        declared_winner = ElectionWinner.objects.filter(
            election=election, position=position
        ).select_related('candidate').first()
        positions_data.append({
            'position': position,
            'candidates': candidates,
            'declared_winner': declared_winner,
        })
    return render(request, 'dashboard/admin_declare_winners.html', {
        'election': election, 'positions_data': positions_data,
    })


@staff_required
def admin_declare_winner_save(request, election_id, position_id):
    election = get_object_or_404(Election, id=election_id)
    position = get_object_or_404(Position, id=position_id, election=election)
    if request.method == 'POST':
        candidate_id = request.POST.get('candidate_id')
        candidate = get_object_or_404(Candidate, id=candidate_id, position=position, status='approved')
        winner, created = ElectionWinner.objects.update_or_create(
            election=election, position=position,
            defaults={'candidate': candidate, 'declared_by': request.user}
        )
        action = 'declared' if created else 'updated'
        messages.success(request, f'{candidate.full_name} {action} as winner for {position.title}.')
    return redirect('dashboard:admin_declare_winners', election_id=election_id)


@staff_required
def admin_undeclare_winner(request, election_id, position_id):
    election = get_object_or_404(Election, id=election_id)
    winner = get_object_or_404(ElectionWinner, election=election, position_id=position_id)
    if request.method == 'POST':
        name = winner.candidate.full_name
        winner.delete()
        messages.success(request, f'Winner declaration for {name} removed.')
    return redirect('dashboard:admin_declare_winners', election_id=election_id)

# ── Achievements ──────────────────────────────────────────────────────────────

@staff_required
def admin_achievements(request):
    achievements = Achievement.objects.select_related(
        'winner__candidate', 'winner__position', 'winner__election', 'reviewed_by'
    ).order_by('-submitted_at')
    status = request.GET.get('status')
    if status:
        achievements = achievements.filter(status=status)
    return render(request, 'dashboard/admin_achievements.html', {
        'achievements': achievements,
        'total': achievements.count(),
        'selected_status': status,
    })


@staff_required
def admin_achievement_review(request, achievement_id):
    achievement = get_object_or_404(Achievement, id=achievement_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            achievement.status = Achievement.STATUS_APPROVED
            achievement.reviewed_by = request.user
            achievement.reviewed_at = timezone.now()
            achievement.save()
            messages.success(request, f'Achievement "{achievement.title}" approved and is now public.')
        elif action == 'reject':
            achievement.status = Achievement.STATUS_REJECTED
            achievement.reviewed_by = request.user
            achievement.reviewed_at = timezone.now()
            achievement.save()
            messages.success(request, f'Achievement "{achievement.title}" rejected.')
    return redirect('dashboard:admin_achievements')


@login_required
def my_achievements(request):
    winner_records = ElectionWinner.objects.filter(
        candidate__student=request.user
    ).select_related('position', 'election', 'candidate').prefetch_related('achievements')
    if not winner_records.exists():
        messages.info(request, 'You have not been declared a winner in any election yet.')
        return redirect('dashboard:student')
    if request.method == 'POST':
        winner_id = request.POST.get('winner_id')
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        winner = get_object_or_404(ElectionWinner, id=winner_id, candidate__student=request.user)
        if not title or not description:
            messages.error(request, 'Please fill in both the title and description.')
        else:
            Achievement.objects.create(winner=winner, title=title, description=description)
            messages.success(request, 'Achievement submitted for admin approval.')
            return redirect('dashboard:my_achievements')
    return render(request, 'dashboard/my_achievements.html', {'winner_records': winner_records})
# ── Analytics ─────────────────────────────────────────────────────────────────

from django.db.models.functions import TruncHour, TruncDate


@staff_required
def admin_analytics(request):
    elections = Election.objects.all().order_by('-start_at')
    selected_election_id = request.GET.get('election')
    selected_election = None
    analytics = None

    # Cross-election comparison — always computed
    cross_election_data = []
    for e in elections:
        total_students = User.objects.filter(
            is_staff=False, is_active=True
        ).count()
        e_votes = Vote.objects.filter(election=e).count()
        e_pct = round((e_votes / total_students * 100), 1) if total_students else 0
        cross_election_data.append({
            'name': e.name,
            'year': e.start_at.year,
            'votes': e_votes,
            'pct': e_pct,
        })

    if selected_election_id:
        selected_election = get_object_or_404(Election, id=selected_election_id)
        total_students = User.objects.filter(
            is_staff=False, is_active=True
        ).count()
        total_votes = Vote.objects.filter(election=selected_election).count()
        turnout_pct = round(
            (total_votes / total_students * 100), 1
        ) if total_students else 0

        # Results by position
        positions_data = []
        for position in selected_election.positions.all().order_by('order'):
            pos_votes = Vote.objects.filter(
                election=selected_election, position=position
            )
            pos_total = pos_votes.count()
            candidates = Candidate.objects.filter(
                election=selected_election,
                position=position,
                status='approved'
            ).annotate(vote_count=Count('votes')).order_by('-vote_count')

            winner = ElectionWinner.objects.filter(
                election=selected_election, position=position
            ).select_related('candidate').first()

            # Competition score — spread between 1st and 2nd place
            candidate_list = list(candidates)
            if len(candidate_list) >= 2:
                top = candidate_list[0].vote_count
                second = candidate_list[1].vote_count
                spread = top - second
                competition = 'High' if spread <= 2 else 'Medium' if spread <= 5 else 'Low'
            elif len(candidate_list) == 1:
                spread = candidate_list[0].vote_count
                competition = 'Uncontested'
            else:
                spread = 0
                competition = 'No candidates'

            # Abstention — eligible students who did not vote
            if position.voting_scope == 'all':
                eligible = User.objects.filter(
                    is_staff=False,
                    is_active=True,
                    is_email_verified=True,
                    can_vote=True
                ).count()
            else:
                eligible = User.objects.filter(
                    is_staff=False,
                    is_active=True,
                    is_email_verified=True,
                    can_vote=True,
                    cohort__in=position.allowed_cohorts.all(),
                    is_cohort_confirmed=True
                ).count()

            abstained = max(eligible - pos_total, 0)
            abstention_pct = round(
                (abstained / eligible * 100), 1
            ) if eligible else 0

            positions_data.append({
                'position': position,
                'total_votes': pos_total,
                'candidates': candidates,
                'winner': winner,
                'competition': competition,
                'spread': spread,
                'eligible': eligible,
                'abstained': abstained,
                'abstention_pct': abstention_pct,
            })

        # Vote timeline — grouped by hour
        timeline = (
            Vote.objects
            .filter(election=selected_election)
            .annotate(hour=TruncHour('cast_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('hour')
        )
        timeline_labels = [
            entry['hour'].strftime('%b %d %H:%M') for entry in timeline
        ]
        timeline_counts = [entry['count'] for entry in timeline]

        # Peak voting hours — group by hour of day (0-23)
        from django.db.models import IntegerField
        from django.db.models.functions import ExtractHour
        peak_hours = (
            Vote.objects
            .filter(election=selected_election)
            .annotate(hour_of_day=ExtractHour('cast_at'))
            .values('hour_of_day')
            .annotate(count=Count('id'))
            .order_by('hour_of_day')
        )
        all_hours = list(range(24))
        peak_map = {entry['hour_of_day']: entry['count'] for entry in peak_hours}
        peak_labels = [f'{h:02d}:00' for h in all_hours]
        peak_counts = [peak_map.get(h, 0) for h in all_hours]

        # Cohort participation
        cohort_data = []
        for cohort in Cohort.objects.all().order_by('year'):
            cohort_votes = Vote.objects.filter(
                election=selected_election,
                voter__cohort=cohort
            ).count()
            cohort_students = User.objects.filter(
                cohort=cohort, is_staff=False
            ).count()
            cohort_pct = round(
                (cohort_votes / cohort_students * 100), 1
            ) if cohort_students else 0
            cohort_data.append({
                'cohort': cohort,
                'votes': cohort_votes,
                'students': cohort_students,
                'pct': cohort_pct,
            })

        # Cohort vs position breakdown
        cohort_position_data = []
        for position in selected_election.positions.all().order_by('order'):
            row = {'position': position, 'cohorts': []}
            for cohort in Cohort.objects.all().order_by('year'):
                votes = Vote.objects.filter(
                    election=selected_election,
                    position=position,
                    voter__cohort=cohort
                ).count()
                row['cohorts'].append({
                    'cohort': cohort,
                    'votes': votes,
                })
            cohort_position_data.append(row)

        # Candidate momentum — votes accumulated over time per candidate
        # for each position independently
        momentum_data = []
        for position in selected_election.positions.all().order_by('order'):
            candidates = Candidate.objects.filter(
                election=selected_election,
                position=position,
                status='approved'
            )
            if not candidates.exists():
                continue

            hours = list(timeline_labels)
            if not hours:
                continue

            candidate_lines = []
            for candidate in candidates:
                hourly = (
                    Vote.objects
                    .filter(election=selected_election, candidate=candidate)
                    .annotate(hour=TruncHour('cast_at'))
                    .values('hour')
                    .annotate(count=Count('id'))
                    .order_by('hour')
                )
                hourly_map = {
                    entry['hour'].strftime('%b %d %H:%M'): entry['count']
                    for entry in hourly
                }
                # Cumulative counts
                cumulative = []
                running = 0
                for label in timeline_labels:
                    running += hourly_map.get(label, 0)
                    cumulative.append(running)

                candidate_lines.append({
                    'name': candidate.full_name,
                    'data': cumulative,
                })

            momentum_data.append({
                'position': position,
                'labels': timeline_labels,
                'candidates': candidate_lines,
            })

        analytics = {
            'total_students': total_students,
            'total_votes': total_votes,
            'turnout_pct': turnout_pct,
            'positions_data': positions_data,
            'timeline_labels': timeline_labels,
            'timeline_counts': timeline_counts,
            'peak_labels': peak_labels,
            'peak_counts': peak_counts,
            'cohort_data': cohort_data,
            'cohort_position_data': cohort_position_data,
            'momentum_data': momentum_data,
        }

    return render(request, 'dashboard/admin_analytics.html', {
        'elections': elections,
        'selected_election': selected_election,
        'analytics': analytics,
        'cross_election_data': cross_election_data,
    })
# ── PDF Export ────────────────────────────────────────────────────────────────

from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm
import io


@staff_required
def export_election_results_pdf(request, election_id):
    election = get_object_or_404(Election, id=election_id)
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    kepler_blue = colors.HexColor('#0d47a1')
    kepler_green = colors.HexColor('#1b5e20')

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        textColor=kepler_blue,
        fontSize=18,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        textColor=colors.HexColor('#555555'),
        fontSize=10,
        spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        textColor=kepler_green,
        fontSize=13,
        spaceBefore=16,
        spaceAfter=8,
    )

    elements = []

    # Header
    elements.append(Paragraph('Kepler College Kigali', subtitle_style))
    elements.append(Paragraph(f'Election Results: {election.name}', title_style))
    elements.append(Paragraph(
        f'{election.start_at.strftime("%B %d, %Y")} — '
        f'{election.end_at.strftime("%B %d, %Y")}',
        subtitle_style
    ))
    elements.append(Spacer(1, 0.5*cm))

    # Summary
    total_votes = Vote.objects.filter(election=election).count()
    total_students = User.objects.filter(is_staff=False, is_active=True).count()
    turnout = round((total_votes / total_students * 100), 1) if total_students else 0

    summary_data = [
        ['Total Students', 'Total Votes', 'Voter Turnout'],
        [str(total_students), str(total_votes), f'{turnout}%'],
    ]
    summary_table = Table(summary_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), kepler_blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, 1), 14),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 1), (-1, 1), kepler_blue),
        ('ROWBACKGROUNDS', (0, 1), (-1, 1), [colors.HexColor('#e3f2fd')]),
        ('BOX', (0, 0), (-1, -1), 1, kepler_blue),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bbdefb')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*cm))

    # Results per position
    for position in election.positions.all().order_by('order'):
        elements.append(Paragraph(position.title, heading_style))

        rows = (
            Vote.objects
            .filter(election=election, position=position)
            .values('candidate__full_name')
            .annotate(votes=Count('id'))
            .order_by('-votes')
        )
        pos_total = sum(r['votes'] for r in rows) or 0

        declared_winner = ElectionWinner.objects.filter(
            election=election, position=position
        ).select_related('candidate').first()

        if rows:
            data = [['Rank', 'Candidate', 'Votes', 'Percentage', 'Status']]
            for i, row in enumerate(rows, 1):
                pct = round((row['votes'] / pos_total * 100), 1) if pos_total else 0
                status = ''
                if declared_winner and declared_winner.candidate.full_name == row['candidate__full_name']:
                    status = '🏆 Winner'
                data.append([
                    str(i),
                    row['candidate__full_name'],
                    str(row['votes']),
                    f'{pct}%',
                    status,
                ])
            data.append(['', 'Total', str(pos_total), '100%', ''])

            table = Table(data, colWidths=[1.5*cm, 7*cm, 2.5*cm, 3*cm, 2.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), kepler_green),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f1f8e9')]),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f5e9')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BOX', (0, 0), (-1, -1), 1, kepler_green),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#c8e6c9')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(table)
        else:
            elements.append(Paragraph('No votes cast for this position.', styles['Normal']))

    # Footer
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        f'Generated by Kepler Student Guild Voting System — '
        f'{timezone.now().strftime("%B %d, %Y at %H:%M")}',
        subtitle_style
    ))

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="{election.name}-results.pdf"'
    )
    return response