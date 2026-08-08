from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from apps.alerts.models import AlertEvent
from apps.billing.models import TrustRelease
from apps.core.models import Company, CompanyMembership
from apps.network_map.models import NetworkElement, NetworkProject

User = get_user_model()
ROOT = Path(__file__).resolve().parents[3]


class TechnicianAppProjectsShapeTests(SimpleTestCase):
    def test_load_projects_handles_real_api_shape(self):
        # /api/map/projects/ sempre devolveu {success, projects: [...]},
        # não {data: {projects}} nem nenhum formato que extractRows()
        # reconhece -- sem isso o seletor de projeto nunca populava.
        source = (ROOT / "static/js/technician-app.js").read_text(encoding="utf-8")
        self.assertIn("Array.isArray(payload?.projects)", source)


def make_company(name):
    return Company.objects.create(
        name=name, slug=slugify(name), company_type=Company.CompanyType.PROVIDER
    )


def make_member(company, username, role, active=True):
    user = User.objects.create_user(username=username, password="Senha123!")
    CompanyMembership.objects.create(company=company, user=user, role=role, active=active)
    return user


class AlertLifecycleTests(TestCase):
    def setUp(self):
        self.company = make_company("Empresa Alertas")
        self.admin = make_member(self.company, "admin_alertas", CompanyMembership.Role.ADMIN)
        self.element = NetworkElement.objects.create(
            company=self.company,
            name="CTO Alerta",
            element_type=NetworkElement.ElementType.CTO,
            point=Point(-46.6, -23.5, srid=4326),
        )
        self.client.force_login(self.admin)

    def make_alert(self, state=AlertEvent.State.OPEN, **extra):
        return AlertEvent.objects.create(
            fingerprint=extra.pop("fingerprint", f"test-{AlertEvent.objects.count()}"),
            company=self.company,
            title="Elemento offline",
            message="Sem resposta SNMP",
            scope="equipment",
            severity="high",
            state=state,
            opened_at=timezone.now(),
            network_element=self.element,
            **extra,
        )

    def test_closed_alert_does_not_appear(self):
        self.make_alert(state=AlertEvent.State.CLOSED)
        response = self.client.get(reverse("company-alerts"))
        self.assertNotContains(response, "Elemento offline")

    def test_open_alert_appears(self):
        self.make_alert(state=AlertEvent.State.OPEN)
        response = self.client.get(reverse("company-alerts"))
        self.assertContains(response, "Elemento offline")

    def test_deleting_element_closes_open_alert(self):
        alert = self.make_alert(state=AlertEvent.State.OPEN)
        self.element.delete()
        alert.refresh_from_db()
        self.assertEqual(alert.state, AlertEvent.State.CLOSED)
        self.assertIsNotNone(alert.closed_at)

    def test_clear_alert_closes_it_and_removes_from_view(self):
        alert = self.make_alert(state=AlertEvent.State.OPEN)
        response = self.client.post(
            reverse("company-alerts"), {"action": "clear_alert", "alert_id": alert.id}
        )
        self.assertEqual(response.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.state, AlertEvent.State.CLOSED)

    def test_clear_all_closes_every_active_alert(self):
        a1 = self.make_alert(state=AlertEvent.State.OPEN, fingerprint="a1")
        a2 = self.make_alert(state=AlertEvent.State.ACKNOWLEDGED, fingerprint="a2")
        self.client.post(reverse("company-alerts"), {"action": "clear_all"})
        a1.refresh_from_db()
        a2.refresh_from_db()
        self.assertEqual(a1.state, AlertEvent.State.CLOSED)
        self.assertEqual(a2.state, AlertEvent.State.CLOSED)

    def test_view_only_member_cannot_clear(self):
        view_user = make_member(self.company, "view_alertas", CompanyMembership.Role.VIEW)
        alert = self.make_alert(state=AlertEvent.State.OPEN)
        self.client.force_login(view_user)
        self.client.post(reverse("company-alerts"), {"action": "clear_alert", "alert_id": alert.id})
        alert.refresh_from_db()
        self.assertEqual(alert.state, AlertEvent.State.OPEN)


class SuperadminCompanyEditTests(TestCase):
    def setUp(self):
        self.company = make_company("Empresa Superadmin")
        self.superuser = User.objects.create_superuser(
            username="root_v085", email="root@test.local", password="Senha123!"
        )
        self.member = make_member(self.company, "membro_v085", CompanyMembership.Role.EDIT)
        self.client.force_login(self.superuser)

    def test_change_role_accepts_all_four_roles(self):
        url = reverse("platform-company-edit", args=[self.company.id])
        for role in ("view", "edit", "admin", "technician"):
            response = self.client.post(
                url, {"action": "change_role", "membership_id": self.member.company_memberships.first().pk, "role": role}
            )
            self.assertEqual(response.status_code, 302)
            self.member.company_memberships.first().refresh_from_db()
            self.assertEqual(self.member.company_memberships.first().role, role)

    def test_edit_page_exposes_whitelabel_fields(self):
        response = self.client.get(reverse("platform-company-edit", args=[self.company.id]))
        self.assertContains(response, 'name="logo"')
        self.assertContains(response, 'name="brand_color"')


class PlatformFinancial500Tests(TestCase):
    def test_orphaned_trust_release_does_not_crash(self):
        company = make_company("Empresa Financeiro")
        superuser = User.objects.create_superuser(
            username="root_fin_v085", email="rootfin@test.local", password="Senha123!"
        )
        TrustRelease.objects.create(
            company=company, requested_by=None, granted_until=timezone.now()
        )
        self.client.force_login(superuser)
        response = self.client.get(reverse("platform-financial-overview"))
        self.assertEqual(response.status_code, 200)


class TechnicianProjectScopeTests(TestCase):
    def setUp(self):
        self.company = make_company("Empresa Escopo")
        self.project_a = NetworkProject.objects.create(company=self.company, name="Projeto A", code="PROJ-A")
        self.project_b = NetworkProject.objects.create(company=self.company, name="Projeto B", code="PROJ-B")
        self.tech = make_member(self.company, "tecnico_v085", CompanyMembership.Role.TECHNICIAN)
        self.client.force_login(self.tech)

    def test_technician_with_no_grants_sees_no_projects(self):
        response = self.client.get("/api/map/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["projects"], [])

    def test_technician_sees_only_granted_project(self):
        membership = self.tech.company_memberships.first()
        membership.technician_projects.add(self.project_a)
        response = self.client.get("/api/map/projects/")
        payload = response.json()["projects"]
        self.assertEqual([p["id"] for p in payload], [self.project_a.id])

    def test_mixed_role_user_is_not_scoped(self):
        other_company = make_company("Empresa Mista")
        mixed_user = User.objects.create_user(username="misto_v085", password="Senha123!")
        CompanyMembership.objects.create(company=self.company, user=mixed_user, role=CompanyMembership.Role.TECHNICIAN, active=True)
        CompanyMembership.objects.create(company=other_company, user=mixed_user, role=CompanyMembership.Role.ADMIN, active=True)
        self.client.force_login(mixed_user)
        response = self.client.get("/api/map/projects/")
        payload = response.json()["projects"]
        self.assertIn(self.project_a.id, [p["id"] for p in payload])

    def test_admin_sets_technician_projects_via_team_page(self):
        admin = make_member(self.company, "admin_escopo", CompanyMembership.Role.ADMIN)
        self.client.force_login(admin)
        membership = self.tech.company_memberships.first()
        response = self.client.post(
            reverse("company-team"),
            {
                "action": "set_technician_projects",
                "membership_id": membership.pk,
                "project_ids": [self.project_a.id, self.project_b.id],
            },
        )
        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual(
            set(membership.technician_projects.values_list("id", flat=True)),
            {self.project_a.id, self.project_b.id},
        )
