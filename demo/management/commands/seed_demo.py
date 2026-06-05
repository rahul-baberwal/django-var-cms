from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from demo.models import Category, Article, Page, MediaAsset

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo data + create role users"

    def handle(self, *args, **options):
        self.stdout.write("Seeding django-var-cms demo…\n")

        # ── Groups / Roles ────────────────────────────────────────────────
        for gname in ("editor", "author", "viewer"):
            Group.objects.get_or_create(name=gname)
        self.stdout.write("  ✓ Groups: superuser, editor, author, viewer")

        # ── Users ─────────────────────────────────────────────────────────
        users = [
            ("admin",  "admin",  True,  None),
            ("editor", "editor", False, "editor"),
            ("author", "author", False, "author"),
            ("viewer", "viewer", False, "viewer"),
            ("alice",  "alice",  False, "viewer"),   # has UserPermission override
        ]
        for username, password, is_super, group in users:
            if not User.objects.filter(username=username).exists():
                if is_super:
                    u = User.objects.create_superuser(username, f"{username}@example.com", password)
                else:
                    u = User.objects.create_user(username, f"{username}@example.com", password)
                    if group:
                        u.groups.add(Group.objects.get(name=group))
                self.stdout.write(f"  ✓ User: {username} / {password}  [{group or 'superuser'}]")

        # ── Categories ────────────────────────────────────────────────────
        cats = []
        for name, slug in [("Technology","technology"),("Design","design"),("Business","business"),("Science","science")]:
            c, _ = Category.objects.get_or_create(slug=slug, defaults={"name": name, "is_active": True})
            cats.append(c)
        self.stdout.write(f"  ✓ {len(cats)} categories")

        # ── Articles ──────────────────────────────────────────────────────
        statuses = ["draft","published","published","archived"]
        for i in range(12):
            Article.objects.get_or_create(slug=f"article-{i+1}", defaults={
                "title":      f"Sample Article #{i+1}",
                "author":     ["Alice","Bob","Carol","Dave"][i%4],
                "body":       f"Article {i+1} body content. " * 10,
                "category":   cats[i%len(cats)],
                "status":     statuses[i%len(statuses)],
                "is_featured": i%5==0,
                "view_count": i*37,
                "rating":     round(3.5+(i%3)*0.5,1),
            })
        self.stdout.write("  ✓ 12 articles")

        # ── Pages ─────────────────────────────────────────────────────────
        for slug, title in [("home","Home"),("about","About Us"),("contact","Contact"),("privacy","Privacy Policy")]:
            Page.objects.get_or_create(slug=slug, defaults={
                "title": title, "body": f"<p>Content for {title}.</p>",
                "is_published": True, "show_in_nav": slug != "privacy",
            })
        self.stdout.write("  ✓ 4 pages")

        # ── Media Assets ──────────────────────────────────────────────────
        for i in range(4):
            MediaAsset.objects.get_or_create(title=f"Sample Asset #{i+1}", defaults={
                "asset_type": ["image","video","audio","document"][i],
                "alt_text": f"Alt text for asset {i+1}",
                "tags": "sample, demo",
                "description": f"This is a sample {['image','video','audio','document'][i]} asset.",
            })
        self.stdout.write("  ✓ 4 media assets (no files — upload via CMS)")

        self.stdout.write(self.style.SUCCESS("""
✅  Done!  →  http://127.0.0.1:8000/var-cms/

Login accounts:
  admin  / admin   (superuser — full access)
  editor / editor  (editor group — add/edit, no delete)
  author / author  (author group — limited field edits)
  viewer / viewer  (viewer group — read-only)
  alice  / alice   (viewer + UserPermission delete override on articles)
"""))
