from django.db import models
from django.contrib.auth import get_user_model


class SoftDeleteManager(models.Manager):

    select_related_list = []

    def get_queryset(self):
        qs = super().get_queryset().filter(deleted=False)
        if self.select_related_list:
            qs = qs.select_related(*self.select_related_list)
        return qs

    def delete(self, *args, **kwargs):
        self.update(deleted=True)


class TimeStampedNameDescriptonOwnerModel(models.Model):
    """
    Abstract Base Class for all models that need a title, description, owner, created and updated fields.
    """
    title = models.CharField(max_length=255)
    description = models.TextField()
    owner = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    llm_context = models.JSONField(default=dict,
                                   help_text="Reserved for use by the LLM")
    deleted = models.BooleanField(default=False)
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    select_related_list = ['owner']

    def __str__(self):
        return self.title

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        self.deleted = True
        self.save()


class Project(TimeStampedNameDescriptonOwnerModel):
    """
    Project model. Projects can have optional deadlines and categories.
    """
    deadline = models.DateTimeField(blank=True, null=True,
                                    help_text='Enter a deadline date (YYYY-MM-DD)')
    category = models.CharField(max_length=100, blank=True)
    tags = models.ManyToManyField('Tag', blank=True)


class Task(TimeStampedNameDescriptonOwnerModel):
    """
    Task model. Tasks can be assigned to users and can be marked as completed.
    """
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent')
    ]
    STATUS_CHOICES = [
        ('TODO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('REVIEW', 'In Review'),
        ('DONE', 'Done')
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    assignees = models.ManyToManyField(get_user_model(), related_name='assigned_tasks')
    depends_on = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True,
                                   help_text='This task depends on another task')
    priority = models.CharField(max_length=6, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=11, choices=STATUS_CHOICES, default='TODO')
    due_date = models.DateTimeField(blank=True, null=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    tags = models.ManyToManyField('Tag', blank=True)
    select_related_list = ['project', 'project__owner']

class Tag(models.Model):
    """
    Tag model for categorizing projects and tasks.
    """
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default="#000000")

    def __str__(self):
        return self.name


class Comment(TimeStampedNameDescriptonOwnerModel):
    """
    Comment model. Comments can be attached to tasks.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    select_related_list = ['task', 'task__project', 'task__project__owner']
