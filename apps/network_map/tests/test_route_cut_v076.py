from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import LineString, MultiLineString, Point
from django.test import SimpleTestCase, TestCase
from django.utils.text import slugify

from apps.core.models import Company, CompanyMembership
from apps.network_map.models import (
    CTO,
    CTOSplitter,
    CTOSplitterPort,
    FiberCable,
    FiberColor,
    FiberStrand,
    FiberTube,
    NetworkElement,
    NetworkProject,
    NetworkRoute,
    NetworkRouteElementMembership,
    SpliceTray,
    SpliceTraySplitter,
    SpliceTraySplitterPort,
)

User = get_user_model()
ROOT = Path(__file__).resolve().parents[3]


class RouteCutV076StaticRegressionTests(SimpleTestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_cut_no_longer_blocks_active_optics(self):
        source = self.read("apps/network_map/api/topology_actions.py")
        self.assertNotIn("Desfaça essas ligações antes de cortá-lo", source)
        self.assertIn("_move_optical_references", source)
        self.assertIn("_auto_cable_name", source)

    def test_route_rules_are_explicit(self):
        source = self.read("apps/network_map/api/optical_editor_v3.py")
        self.assertIn("Essa CTO já tem rota.", source)
        self.assertIn("NetworkRouteElementMembership", source)

    def test_splitter_port_supports_real_drop_and_pppoe(self):
        models_source = self.read("apps/network_map/models.py")
        views_source = self.read("apps/network_map/api/map_master_views.py")
        self.assertIn("direct_drop_cable", models_source)
        self.assertIn('"pppoe": port.access_point.username', views_source)
        self.assertIn("CTOSplitterPort.Status.OCCUPIED", views_source)
        self.assertIn("SpliceTraySplitterPort.objects.filter", views_source)
        self.assertIn("manual_canvas", views_source)

    def test_map_ui_exposes_route_and_cut_actions(self):
        cable_ui = self.read("static/js/map-v07539-suite.js")
        element_ui = self.read("static/js/map-v0758-core-ui.js")
        editor = self.read("static/js/map-editor.js")
        self.assertIn("Adicionar na rota", cable_ui)
        self.assertIn("Realizar corte", cable_ui)
        self.assertIn("Adicionar na rota", element_ui)
        self.assertNotIn(
            '<div class="unifilar-input">Entrada do splitter</div><div class="unifilar-line"></div>',
            editor,
        )

    def test_optical_workspace_divider_line_removed(self):
        # A view real usada em produção pra abrir fusões de CTO/CEO/CDO é o
        # IXCOpticalWorkspace (canvas), não o #unifilar-dialog legado -- o
        # traço fixo de "risco" ficava em drawDistributionDivider() aqui,
        # desenhado sempre, sem relação com nenhuma fibra/conexão real. O
        # handoff não mexeu neste arquivo -- achei e corrigi na revisão.
        renderer = self.read("static/js/optical/optical-renderer.js")
        start = renderer.index("function drawDistributionDivider")
        end = renderer.index("function drawGrid", start)
        block = renderer[start:end]
        self.assertNotIn("ctx.beginPath()", block)
        self.assertNotIn("ctx.stroke()", block)
        self.assertIn("ENTRADA / CHEGADA", block)
        self.assertIn("SAÍDA / DISTRIBUIÇÃO", block)

    def test_optical_workspace_css_divider_removed(self):
        # Segunda linha fixa, independente da do canvas: um par de
        # pseudo-elementos CSS (::before/::after) em
        # .ixc-optical-stage-has-divider, aplicado incondicionalmente no
        # template do workspace óptico. O handoff também não tocou nisso --
        # sem essa correção, a linha e o rótulo duplicado continuavam
        # aparecendo por cima do canvas já corrigido.
        workspace_js = self.read("static/js/optical/optical-workspace.js")
        self.assertNotIn("ixc-optical-stage-has-divider", workspace_js)
        css_v07535 = self.read("static/css/map-optical-workspace-v07535.css")
        self.assertNotIn("has-divider", css_v07535)
        css_v07539 = self.read("static/css/map-v07539-suite.css")
        self.assertNotIn("has-divider", css_v07539)


def make_company(name):
    return Company.objects.create(
        name=name, slug=slugify(name), company_type=Company.CompanyType.PROVIDER
    )


class RouteCutFunctionalTestBase(TestCase):
    def setUp(self):
        self.company = make_company("Empresa Corte")
        self.project = NetworkProject.objects.create(
            company=self.company, name="Projeto Corte", code="PROJ-CORTE"
        )
        self.user = User.objects.create_user(username="admin_corte", password="Senha123!")
        CompanyMembership.objects.create(
            company=self.company, user=self.user, role=CompanyMembership.Role.ADMIN, active=True
        )
        self.color = FiberColor.objects.create(code="AZ", name="Azul", hex_color="#0000FF")
        self.client.force_login(self.user)

    def make_element(self, name, element_type, lon, lat, cls=NetworkElement, **extra):
        return cls.objects.create(
            company=self.company,
            project=self.project,
            name=name,
            element_type=element_type,
            point=Point(lon, lat, srid=4326),
            **extra,
        )

    def make_cable(self, name, origin, destination, coords, fiber_count=12):
        cable = FiberCable.objects.create(
            company=self.company,
            project=self.project,
            name=name,
            code=name,
            cable_type=FiberCable.CableType.DISTRIBUTION,
            geometry=MultiLineString(LineString(coords, srid=4326), srid=4326),
            fiber_count=fiber_count,
            origin=origin,
            destination=destination,
        )
        tube = FiberTube.objects.create(cable=cable, number=1, color=self.color)
        for number in range(1, fiber_count + 1):
            FiberStrand.objects.create(
                cable=cable,
                tube=tube,
                number=number,
                position_in_tube=number,
                color=self.color,
                status=FiberStrand.Status.FREE,
            )
        return cable


class CutPreservesOpticsTests(RouteCutFunctionalTestBase):
    """TESTE OBRIGATÓRIO 1: corte com fusão ativa no lado posterior."""

    def setUp(self):
        super().setUp()
        self.cto1 = self.make_element("CTO 1", NetworkElement.ElementType.CTO, -46.60, -23.55, cls=CTO)
        self.cto2 = self.make_element("CTO 2", NetworkElement.ElementType.CTO, -46.50, -23.55, cls=CTO)
        self.cto3 = self.make_element("CTO 3", NetworkElement.ElementType.CTO, -46.40, -23.55, cls=CTO)
        self.cable = self.make_cable(
            "CABO CTO 1 → CTO 3 12 F",
            self.cto1,
            self.cto3,
            [(-46.60, -23.55), (-46.50, -23.55), (-46.40, -23.55)],
        )

        # Splitter hospedado na própria caixa do corte (CTO 2): input_fiber
        # (chegada) deve ficar no 1o trecho, output_fiber (distribuição) deve
        # migrar pro 2o trecho -- semântica descrita no handoff.
        first_fiber = self.cable.fibers.get(number=1)
        second_fiber = self.cable.fibers.get(number=2)
        tray = SpliceTray.objects.create(splice_box=self.cto2, number=1)
        self.splitter = SpliceTraySplitter.objects.create(
            tray=tray, position=1, ratio=CTOSplitter.Ratio.ONE_TO_8, input_fiber=first_fiber
        )
        self.splitter_port = SpliceTraySplitterPort.objects.create(
            splitter=self.splitter, number=1, output_fiber=second_fiber
        )

        # Fusão numa fibra genuinamente a jusante (mais perto de CTO 3 do
        # que de CTO 2) -- valida o fallback geométrico de downstream.
        third_fiber = self.cable.fibers.get(number=3)
        self.downstream_dio = self.make_element(
            "DIO Downstream", NetworkElement.ElementType.DIO, -46.42, -23.55
        )
        self.downstream_splitter = SpliceTraySplitter.objects.create(
            tray=SpliceTray.objects.create(splice_box=self.downstream_dio, number=1),
            position=1,
            ratio=CTOSplitter.Ratio.ONE_TO_8,
            input_fiber=third_fiber,
        )

    def cut(self):
        return self.client.post(
            f"/api/map/elements/{self.cto2.id}/cables/{self.cable.id}/cut/",
            data={},
            content_type="application/json",
        )

    def test_cut_returns_201_with_two_named_segments(self):
        response = self.cut()
        self.assertEqual(response.status_code, 201, response.content)
        payload = response.json()
        names = [c["name"] for c in payload["cables"]]
        self.assertIn("CABO CTO 1 → CTO 2 12 F", names)
        self.assertIn("CABO CTO 2 → CTO 3 12 F", names)

    def test_cut_creates_two_cables_with_same_fiber_count(self):
        self.cut()
        self.cable.refresh_from_db()
        second = FiberCable.objects.exclude(pk=self.cable.pk).get(project=self.project)
        self.assertEqual(self.cable.destination_id, self.cto2.id)
        self.assertEqual(second.origin_id, self.cto2.id)
        self.assertEqual(second.destination_id, self.cto3.id)
        self.assertEqual(self.cable.fibers.count(), second.fibers.count())

    def test_input_fiber_at_cut_box_stays_on_first_segment(self):
        self.cut()
        self.splitter.refresh_from_db()
        self.assertEqual(self.splitter.input_fiber.cable_id, self.cable.id)

    def test_output_fiber_at_cut_box_moves_to_second_segment(self):
        self.cut()
        second = FiberCable.objects.exclude(pk=self.cable.pk).get(project=self.project)
        self.splitter_port.refresh_from_db()
        self.assertEqual(self.splitter_port.output_fiber.cable_id, second.id)

    def test_downstream_fusion_migrates_to_second_segment_without_error(self):
        response = self.cut()
        self.assertEqual(response.status_code, 201, response.content)
        second = FiberCable.objects.exclude(pk=self.cable.pk).get(project=self.project)
        self.downstream_splitter.refresh_from_db()
        self.assertEqual(self.downstream_splitter.input_fiber.cable_id, second.id)

    def test_cut_does_not_ask_to_undo_fusions(self):
        response = self.cut()
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("Desfaça", response.content.decode())

    def test_cutting_again_at_same_element_is_a_safe_noop(self):
        self.cut()
        response = self.cut()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("already_cut"))


class RouteExclusivityTests(RouteCutFunctionalTestBase):
    """TESTE OBRIGATÓRIO 2: CTO só pode pertencer a uma rota."""

    def setUp(self):
        super().setUp()
        self.route_a = NetworkRoute.objects.create(
            company=self.company, project=self.project, name="Rota A", code="ROTA-A"
        )
        self.route_b = NetworkRoute.objects.create(
            company=self.company, project=self.project, name="Rota B", code="ROTA-B"
        )
        self.cto = self.make_element("CTO 10", NetworkElement.ElementType.CTO, -46.6, -23.5, cls=CTO)

    def assign(self, route):
        return self.client.post(
            "/api/map/assets/route/",
            data={"element_id": self.cto.id, "route_id": route.id},
            content_type="application/json",
        )

    def test_first_assignment_succeeds(self):
        response = self.assign(self.route_a)
        self.assertEqual(response.status_code, 200, response.content)
        self.cto.refresh_from_db()
        self.assertEqual(self.cto.route_id, self.route_a.id)

    def test_second_route_is_rejected_with_409(self):
        self.assign(self.route_a)
        response = self.assign(self.route_b)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Essa CTO já tem rota.")
        self.cto.refresh_from_db()
        self.assertEqual(self.cto.route_id, self.route_a.id)


class RouteSharedMembershipTests(RouteCutFunctionalTestBase):
    """TESTE OBRIGATÓRIO 3: CEO/CDO pode estar em várias rotas."""

    def setUp(self):
        super().setUp()
        self.route_a = NetworkRoute.objects.create(
            company=self.company, project=self.project, name="Rota A", code="ROTA-A"
        )
        self.route_b = NetworkRoute.objects.create(
            company=self.company, project=self.project, name="Rota B", code="ROTA-B"
        )
        self.ceo = self.make_element("CEO 01", NetworkElement.ElementType.SPLICE_BOX, -46.6, -23.5)

    def assign(self, route):
        return self.client.post(
            "/api/map/assets/route/",
            data={"element_id": self.ceo.id, "route_id": route.id},
            content_type="application/json",
        )

    def test_same_ceo_joins_two_routes(self):
        r1 = self.assign(self.route_a)
        r2 = self.assign(self.route_b)
        self.assertEqual(r1.status_code, 200, r1.content)
        self.assertEqual(r2.status_code, 200, r2.content)
        memberships = NetworkRouteElementMembership.objects.filter(element=self.ceo)
        self.assertEqual(memberships.count(), 2)
        self.assertEqual(
            set(memberships.values_list("route_id", flat=True)),
            {self.route_a.id, self.route_b.id},
        )


class RouteCreationTests(RouteCutFunctionalTestBase):
    """TESTE OBRIGATÓRIO 6 (backend): criação de rota via POST."""

    def test_create_route_generates_unique_code(self):
        response = self.client.post(
            "/api/map/routes/",
            data={"project_id": self.project.id, "name": "Rota Centro"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        route = NetworkRoute.objects.get(pk=response.json()["route"]["id"])
        self.assertEqual(route.name, "Rota Centro")
        self.assertTrue(route.code)


class SplitterOccupationTests(RouteCutFunctionalTestBase):
    """TESTE OBRIGATÓRIO 4 e 5: ocupação PPPoE/ERP e DROP físico."""

    def setUp(self):
        super().setUp()
        self.cto = self.make_element("CTO PPPoE", NetworkElement.ElementType.CTO, -46.6, -23.5, cls=CTO)
        self.splitter = CTOSplitter.objects.create(cto=self.cto, ratio=CTOSplitter.Ratio.ONE_TO_8)
        self.port = CTOSplitterPort.objects.create(splitter=self.splitter, number=1)

    def patch_port(self, payload):
        return self.client.patch(
            f"/api/map/master/ctos/{self.cto.id}/splitter-ports/",
            data={**payload, "port_id": self.port.id},
            content_type="application/json",
        )

    def test_pppoe_occupies_port_without_creating_fiber_strand(self):
        from apps.access.models import AccessPoint

        access_point = AccessPoint.objects.create(
            company=self.company,
            source="ixc",
            external_id="123",
            username="cliente.pppoe",
            customer_name="Cliente Teste",
        )
        before = FiberStrand.objects.count()
        response = self.patch_port({"access_point_id": access_point.id})
        self.assertEqual(response.status_code, 200, response.content)
        self.port.refresh_from_db()
        self.assertEqual(self.port.status, CTOSplitterPort.Status.OCCUPIED)
        self.assertEqual(FiberStrand.objects.count(), before)

    def test_drop_cable_occupies_port(self):
        drop_cable = FiberCable.objects.create(
            company=self.company,
            project=self.project,
            name="DROP 01",
            code="DROP-01",
            cable_type=FiberCable.CableType.DROP,
        )
        response = self.patch_port({"direct_drop_cable_id": drop_cable.id})
        self.assertEqual(response.status_code, 200, response.content)
        self.port.refresh_from_db()
        self.assertEqual(self.port.status, CTOSplitterPort.Status.OCCUPIED)
        self.assertEqual(self.port.direct_drop_cable_id, drop_cable.id)

    def test_same_drop_cannot_occupy_two_ports(self):
        drop_cable = FiberCable.objects.create(
            company=self.company,
            project=self.project,
            name="DROP 02",
            code="DROP-02",
            cable_type=FiberCable.CableType.DROP,
        )
        other_port = CTOSplitterPort.objects.create(splitter=self.splitter, number=2)
        other_port.direct_drop_cable = drop_cable
        other_port.save(update_fields=["direct_drop_cable"])

        response = self.patch_port({"direct_drop_cable_id": drop_cable.id})
        self.assertEqual(response.status_code, 409)
