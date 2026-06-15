from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from .models import Job
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import Application
from .models import Notification
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from rest_framework.generics import ListAPIView
from .api import JobSerializer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .models import InterviewQuestion, InterviewAnswer



def home(request):
    return render(request, 'home.html')


def job_list(request):
    query = request.GET.get('q')
    job_list = Job.objects.all()

    if query:
        job_list = job_list.filter(title__icontains=query)

    paginator = Paginator(job_list, 6)
    page = request.GET.get('page')
    jobs = paginator.get_page(page)

    for job in jobs:
        applied_count = Application.objects.filter(job=job).count()
        job.remaining_vacancies = job.total_vacancies - applied_count

    return render(request, 'jobs.html', {'jobs': jobs})



def job_detail(request, id):
    job = get_object_or_404(Job, id=id)


    applied_count = Application.objects.filter(job=job).count()
    job.remaining_vacancies = job.total_vacancies - applied_count

    return render(request, 'job_detail.html', {'job': job})

def register(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully! Please login.")
        return redirect('login')

    return render(request, 'register.html')



def user_login(request):

    if request.method == "POST":

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user is not None:

            # ❌ BLOCK ADMIN FROM USER LOGIN
            if user.is_staff:
                messages.error(request, "Admin must login using Admin Login page")
                return render(request, 'login.html')

            login(request, user)
            return redirect('job_list')

        else:
            messages.error(request, "Invalid username or password")

    return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('home')



@login_required(login_url='login')
def apply_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)


    if Application.objects.filter(job=job, user=request.user).exists():
        messages.warning(request, "You have already applied for this job.")
        return redirect('job_detail', id=job.id)

    if request.method == 'POST':
        Application.objects.create(
            job=job,
            user=request.user,
            full_name=request.POST.get('full_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            skills=request.POST.get('skills'),
            experience=request.POST.get('experience'),
            qualification=request.POST.get('qualification'),
            resume=request.FILES.get('resume')
        )
        Notification.objects.create(
            message=f"{request.user.username} applied for {job.title}",
            job=job
        )


        messages.success(request, "Application submitted successfully!")
        return redirect('job_detail', id=job.id)

    return render(request, 'apply.html', {'job': job})


@login_required
def candidate_dashboard(request):
    apps = Application.objects.filter(applicant=request.user)
    return render(request, 'candidate_dashboard.html', {'apps': apps})

@login_required
def post_job(request):
    if request.method == 'POST':
        Job.objects.create(
            title=request.POST['title'],
            company=request.POST['company'],
            location=request.POST['location'],
            description=request.POST['description'],
            job_type=request.POST['job_type'],
            posted_by=request.user
        )
        return redirect('home')

    return render(request, 'post_job.html')

class JobAPI(ListAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer


def recommended_jobs(request):

    skill = request.GET.get("skill", "")

    jobs = Job.objects.all()

    job_texts = []

    for job in jobs:
        text = job.title + " " + job.company + " " + job.location
        job_texts.append(text)

    job_texts.append(skill)

    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform(job_texts)

    similarity = cosine_similarity(vectors[-1], vectors[:-1])

    scores = list(enumerate(similarity[0]))

    scores = sorted(scores, key=lambda x: x[1], reverse=True)

    recommended = []

    for i in scores[:6]:
        if i[1] > 0.1:
            recommended.append(jobs[i[0]])

    return render(request, "recommend.html", {"jobs": recommended})

@staff_member_required
def admin_dashboard(request):
    job_id = request.GET.get('job_id')

    if job_id:
        applications = Application.objects.filter(
            job_id=job_id
        ).select_related('job', 'user').order_by('-applied_on')
    else:
        applications = Application.objects.select_related(
            'job', 'user'
        ).order_by('-applied_on')

    return render(request, 'admin_dashboard.html', {
        'applications': applications
    })

@staff_member_required
def view_application(request, app_id):
    application = get_object_or_404(Application, id=app_id)

    return render(request, 'view_application.html', {
        'app': application
    })

def reject_application(request, app_id):
    application = Application.objects.get(id=app_id)

    if request.method == "POST":
        reason = request.POST.get("reason")

        application.status = "Rejected"
        application.rejection_reason = reason
        application.save()

        return redirect('admin_dashboard')

    return render(request, 'reject_reason.html', {'application': application})

@login_required
def my_jobs(request):

    applications = Application.objects.filter(user=request.user)

    return render(request, "my_jobs.html", {
        "applications": applications
    })



def interview_bot(request):

    questions = list(InterviewQuestion.objects.all().order_by('id'))

    q_index = request.session.get('q_index', 0)


    if q_index == 0:
        InterviewAnswer.objects.filter(user=request.user).delete()


    if q_index >= len(questions):


        answers = InterviewAnswer.objects.filter(user=request.user)

        total_score = sum(a.score for a in answers)
        max_score = len(questions) * 10

        percentage = (total_score / max_score) * 100 if max_score > 0 else 0


        if percentage >= 80:
            final_feedback = "Excellent performance! You are interview ready."
        elif percentage >= 60:
            final_feedback = "Good job! Improve a bit more."
        elif percentage >= 40:
            final_feedback = "Average performance. Needs improvement."
        else:
            final_feedback = "You need more practice."


        request.session['q_index'] = 0

        return render(request, "interview_result.html", {
            "question": "Interview Completed",
            "answer": "Done!",
            "feedback": final_feedback,
            "score": total_score,
            "total": max_score
        })


    question = questions[q_index]

    if request.method == "POST":
        answer_text = request.POST.get("answer", "").strip()

        words = answer_text.split()
        length = len(words)


        if length == 0:
            score = 0
            feedback = "No answer provided."

        elif length < 10:
            score = 3
            feedback = "Answer is too short. Try to explain more."

        elif length < 20:
            score = 5
            feedback = "Basic answer, try to add more details."

        elif length < 40:
            score = 7
            feedback = "Good answer, but can be improved with examples."

        elif length < 60:
            score = 9
            feedback = "Very good answer with clear explanation."

        else:
            score = 10
            feedback = "Excellent answer with detailed explanation!"


        InterviewAnswer.objects.create(
            user=request.user,
            question=question,
            answer=answer_text,
            feedback=feedback,
            score=score
        )

        # ➡ NEXT QUESTION
        request.session['q_index'] = q_index + 1

        return redirect('interview_bot')

    return render(request, "interview_bot.html", {
        "question": question,
        "q_number": q_index + 1,
        "total": len(questions)
    })


def reset_interview(request):
    request.session['q_index'] = 0


    InterviewAnswer.objects.filter(user=request.user).delete()

    return redirect('interview_bot')

@staff_member_required
def admin_notifications(request):
    notifications = Notification.objects.all().order_by('-created_at')

    return render(request, "admin_notifications.html", {
        "notifications": notifications
    })

@staff_member_required
def update_status(request, app_id, status):
    application = get_object_or_404(Application, id=app_id)

    application.status = status
    application.save()

    return redirect('admin_dashboard')




def admin_login(request):

    if request.method == 'POST':

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        # ONLY ADMIN CAN LOGIN HERE
        if user is not None and user.is_staff:

            login(request, user)

            return redirect('admin_dashboard')

        else:

            return render(
                request,
                'admin_login.html',
                {'error': 'Invalid Admin Credentials'}
            )

    return render(request, 'admin_login.html')