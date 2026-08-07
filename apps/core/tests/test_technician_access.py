from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.access import is_technician_only
from apps.core.models import Company, CompanyMembership
from apps.network_map.models import NetworkElement, NetworkProject

User = get_user_model()


def make_company(name):
    return Company.objects.create(name=name, company_type=Company.CompanyType.PROVIDER)


def make_member(company, username, role, active=True):
    user = User.objects.create_user(username=username, password="Senha123!")
    CompanyMembership.objects.create(company=company, user=user, role=role, active=active)
    return user


class TechnicianAccessTests(TestCase):
    def setUp(self):
        self.company = make_company("Empresa A")
        self.other_company = make_company("Empresa B")

        self.admin_user = make_member(self.company, "admin1", CompanyMembership.Role.ADMIN)
        self.edit_user = make_member(self.company, "edit1", CompanyMembership.Role.EDIT)
        self.view_user = make_member(self.company, "view1", CompanyMembership.Role.VIEW)
        self.tech_user = make_member(self.company, "tech1", CompanyMembership.Role.TECHNICIAN)

        self.project = NetworkProject.objects.create(
            company=self.company, name="Projeto A", code="PROJ-A"
        )
        self.element = NetworkElement.objects.create(
            company=self.company,
            project=self.project,
            name="CTO teste",
            element_type=NetworkElement.ElementType.CTO,
            point="POINT(-46.63 -23.55)",
        )
        self.other_element = NetworkElement.objects.create(
            company=self.other_company,
            name="CTO fora do tenant",
            element_type=NetworkElement.ElementType.CTO,
            point="POINT(-46.63 -23.55)",
        )

    # 2. ADMIN acessa gestão de equipe e edita mapa.
    def test_admin_can_manage_team(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("company-team"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Minha equipe")

    def test_admin_can_write_map(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            f"/api/map/elements/{self.element.id}/position/",
            data={"lat": -23.5, "lng": -46.6},
            content_type="application/json",
        )
        self.assertNotEqual(response.status_code, 403)

    # 3. EDIT edita mapa, mas não acessa gestão de equipe.
    def test_edit_cannot_manage_team(self):
        self.client.force_login(self.edit_user)
        response = self.client.get(reverse("company-team"))
        self.assertEqual(response.status_code, 302)

    def test_edit_can_write_map(self):
        self.client.force_login(self.edit_user)
        response = self.client.post(
            f"/api/map/elements/{self.element.id}/position/",
            data={"lat": -23.5, "lng": -46.6},
            content_type="application/json",
        )
        self.assertNotEqual(response.status_code, 403)

    # 4. VIEW não grava no mapa.
    def test_view_cannot_write_map(self):
        self.client.force_login(self.view_user)
        response = self.client.post(
            f"/api/map/elements/{self.element.id}/position/",
            data={"lat": -23.5, "lng": -46.6},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    # 5/6. TÉCNICO é sempre redirecionado pro /app/, mesmo tentando outra rota.
    def test_technician_redirected_from_dashboard_to_app(self):
        self.client.force_login(self.tech_user)
        response = self.client.get("/")
        self.assertRedirects(response, reverse("technician-app"), fetch_redirect_response=False)

    def test_technician_redirected_from_map_to_app(self):
        self.client.force_login(self.tech_user)
        response = self.client.get("/mapa/")
        self.assertRedirects(response, reverse("technician-app"), fetch_redirect_response=False)

    def test_technician_redirected_from_team_page_to_app(self):
        self.client.force_login(self.tech_user)
        response = self.client.get(reverse("company-team"))
        self.assertRedirects(response, reverse("technician-app"), fetch_redirect_response=False)

    def test_technician_can_open_app(self):
        self.client.force_login(self.tech_user)
        response = self.client.get(reverse("technician-app"))
        self.assertEqual(response.status_code, 200)

    # 7. TÉCNICO consegue GET dos endpoints do próprio tenant.
    def test_technician_can_read_map_api(self):
        self.client.force_login(self.tech_user)
        response = self.client.get(f"/api/map/elements/?project_id={self.project.id}")
        self.assertEqual(response.status_code, 200)

    # 8. TÉCNICO recebe 403 em escrita na API do mapa.
    def test_technician_gets_403_on_map_write(self):
        self.client.force_login(self.tech_user)
        response = self.client.post(
            "/api/map/elements/create/",
            data={},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    # 9. TÉCNICO não lê dado de empresa fora do seu escopo.
    def test_technician_does_not_see_other_company_elements(self):
        self.client.force_login(self.tech_user)
        response = self.client.get("/api/map/elements/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        ids = [feature["properties"]["id"] for feature in payload.get("features", [])]
        self.assertIn(self.element.id, ids)
        self.assertNotIn(self.other_element.id, ids)

    # 10. Técnico numa empresa + outro papel em outra não é technician-only.
    def test_mixed_role_user_is_not_technician_only(self):
        mixed_user = User.objects.create_user(username="mixed1", password="Senha123!")
        CompanyMembership.objects.create(
            company=self.company, user=mixed_user, role=CompanyMembership.Role.TECHNICIAN, active=True
        )
        CompanyMembership.objects.create(
            company=self.other_company, user=mixed_user, role=CompanyMembership.Role.ADMIN, active=True
        )
        self.assertFalse(is_technician_only(mixed_user))

    def test_pure_technician_is_technician_only(self):
        self.assertTrue(is_technician_only(self.tech_user))

    # 11. /app/sw.js serve JS com o header de escopo certo.
    def test_service_worker_route_and_scope_header(self):
        self.client.force_login(self.tech_user)
        response = self.client.get(reverse("technician-service-worker"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Service-Worker-Allowed"], "/app/")
        self.assertIn("javascript", response["Content-Type"])

    # 12. /app/ exige autenticação.
    def test_app_requires_login(self):
        response = self.client.get(reverse("technician-app"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    # Migration de compatibilidade: sem membros 'edit' remanescentes com
    # privilégio administrativo -- ver apps/core/migrations/0014.
    def test_no_literal_edit_role_gate_left_for_admin_only_pages(self):
        self.client.force_login(self.edit_user)
        for name in (
            "company-team",
            "company-branding",
            "company-email-settings",
            "company-snmp-defaults",
        ):
            response = self.client.get(reverse(name))
            self.assertEqual(
                response.status_code, 302, f"{name} deveria redirecionar EDIT (não-admin)"
            )
