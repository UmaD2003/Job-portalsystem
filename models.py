from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

JOB_TYPES = (
    ('Full Time', 'Full Time'),
    ('Part Time', 'Part Time'),
    ('Internship', 'Internship'),
)

class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    qualification = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    description = models.TextField()
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    salary = models.CharField(max_length=100, blank=True)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    total_vacancies = models.IntegerField(default=1)

    def __str__(self):
        return self.title


class Application(models.Model):
    job = models.ForeignKey('Job', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    qualification = models.CharField(max_length=200)
    skills = models.TextField(null=True, blank=True)
    experience = models.CharField(max_length=50, null=True, blank=True)
    resume = models.FileField(upload_to='resumes/', null=True, blank=True)
    applied_on = models.DateTimeField(default=timezone.now)

    status = models.CharField(
        max_length=20,
        choices=[
            ('Pending', 'Pending'),
            ('Approved', 'Approved'),
            ('Rejected', 'Rejected')
        ],
        default='Pending'
    )
    rejection_reason = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} - {self.job.title}"


class InterviewQuestion(models.Model):
    question = models.TextField()

    def __str__(self):
        return self.question


class InterviewAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(InterviewQuestion, on_delete=models.CASCADE)
    answer = models.TextField()
    feedback = models.TextField(blank=True, null=True)
    score = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    message = models.TextField()
    job = models.ForeignKey('Job', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message