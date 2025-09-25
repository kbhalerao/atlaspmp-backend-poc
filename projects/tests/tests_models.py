from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from projects.models import Project, Task, Tag, Comment


class ProjectAppTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.owner = self.User.objects.create_user(email="owner@example.com", password="pass1234")
        self.other = self.User.objects.create_user(email="other@example.com", password="pass1234")

    def test_create_tag_unique(self):
        tag = Tag.objects.create(name="urgent", color="#ff0000")
        self.assertEqual(str(tag), "urgent")
        with self.assertRaises(Exception):
            Tag.objects.create(name="urgent", color="#00ff00")

    def test_create_project_with_optional_fields(self):
        proj = Project.objects.create(
            title="Soil Analysis",
            description="Analyze soil samples",
            owner=self.owner,
            deadline=None,
            category="Research",
        )
        self.assertEqual(str(proj), "Soil Analysis")
        self.assertIsNone(proj.deadline)
        self.assertEqual(proj.category, "Research")
        # tags m2m blank allowed
        self.assertEqual(proj.tags.count(), 0)

        # add tags
        t1 = Tag.objects.create(name="soil", color="#123456")
        t2 = Tag.objects.create(name="lab", color="#654321")
        proj.tags.add(t1, t2)
        self.assertEqual(set(proj.tags.values_list("name", flat=True)), {"soil", "lab"})

    def test_task_creation_and_relations(self):
        proj = Project.objects.create(title="P1", description="desc", owner=self.owner)
        task = Task.objects.create(
            title="T1",
            description="task desc",
            owner=self.owner,
            project=proj,
            priority="HIGH",
            status="TODO",
        )
        # default fields
        self.assertEqual(task.priority, "HIGH")
        self.assertEqual(task.status, "TODO")
        self.assertIsNone(task.depends_on)
        self.assertIsNone(task.due_date)
        self.assertIsNone(task.estimated_hours)
        # m2m assignees and tags
        task.assignees.add(self.owner, self.other)
        self.assertEqual(task.assignees.count(), 2)
        t = Tag.objects.create(name="backend", color="#0000ff")
        task.tags.add(t)
        self.assertEqual(task.tags.count(), 1)

    def test_task_choice_validation(self):
        proj = Project.objects.create(title="P2", description="desc", owner=self.owner)
        task = Task(
            title="Bad",
            description="desc",
            owner=self.owner,
            project=proj,
            priority="MEDIUM",
            status="IN_PROGRESS",
        )
        # Should save fine with valid choices
        task.save()
        # Invalid choice should raise when full_clean is called
        task.priority = "INVALID"
        with self.assertRaises(Exception):
            task.full_clean()

    def test_comment_attached_to_task(self):
        proj = Project.objects.create(title="P3", description="desc", owner=self.owner)
        task = Task.objects.create(title="T3", description="d", owner=self.owner, project=proj)
        comment = Comment.objects.create(title="Note", description="Looks good", owner=self.other, task=task)
        self.assertEqual(str(comment), "Note")
        self.assertEqual(comment.task_id, task.id)
        # timestamps auto-populated
        self.assertIsNotNone(comment.created)
        self.assertIsNotNone(comment.updated)
        self.assertLessEqual(comment.created, timezone.now())
    
    def test_soft_delete(self):
        proj = Project.objects.create(title="Project to delete", description="Will be deleted", owner=self.owner)
        proj_id = proj.id

        # Delete the project
        proj.delete()

        # Object should still exist in DB
        proj_from_db = Project.all_objects.get(id=proj_id)
        self.assertTrue(proj_from_db.deleted)

        # Object should not be returned in normal queries
        self.assertEqual(Project.objects.count(), 0)
        self.assertEqual(Project.all_objects.filter(deleted=True).count(), 1)
