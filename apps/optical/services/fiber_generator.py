from apps.network_map.services import FiberStructureError, generate_cable_fibers


class FiberGenerator:
    """Compatibilidade com o gerador legado.

    A implementação anterior exigia color_standard no modelo e interrompia a
    criação do cabo antes de o importador aplicar o fallback de cores. A fonte
    de verdade agora é network_map.services.generate_cable_fibers(), que usa o
    padrão configurado quando existe e a paleta FiberColor quando não existe.
    """

    def __init__(self, cable):
        self.cable = cable

    def generate(self):
        try:
            return generate_cable_fibers(self.cable)
        except FiberStructureError as exc:
            if "já possui tubos ou fibras" in str(exc):
                return {
                    "cable": self.cable,
                    "tube_count": self.cable.tubes.count(),
                    "fiber_count": self.cable.fibers.count(),
                }
            raise ValueError(str(exc)) from exc
