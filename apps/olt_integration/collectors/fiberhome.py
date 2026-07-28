from .base import BaseOLTCollector


class FiberHomeCollector(BaseOLTCollector):
    """Contrato inicial do coletor FiberHome.

    Os OIDs serão cadastrados por modelo/firmware na próxima etapa para evitar
    acoplamento a uma única família de OLT.
    """

    def __init__(self, olt):
        self.olt = olt

    def test_connection(self) -> dict:
        return {
            "ok": False,
            "message": "Coletor FiberHome aguardando perfil de OIDs.",
        }

    def collect_onus(self) -> list[dict]:
        return []
