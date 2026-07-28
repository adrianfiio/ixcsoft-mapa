from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import (
    OLTViewSet,
    PONPortViewSet,
    ONUViewSet,
    CTOViewSet,
    NetworkRouteViewSet,
    NetworkElementViewSet,
    FiberCableViewSet,
    AlertEventViewSet,
)
from .views import health_check, liveness_check, readiness_check

router = DefaultRouter()
router.register("olts", OLTViewSet)
router.register("pon-ports", PONPortViewSet)
router.register("onus", ONUViewSet)
router.register("ctos", CTOViewSet)
router.register("routes", NetworkRouteViewSet)
router.register("network-elements", NetworkElementViewSet)
router.register("fiber-cables", FiberCableViewSet)
router.register("alerts", AlertEventViewSet)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("health/live/", liveness_check, name="liveness-check"),
    path("health/ready/", readiness_check, name="readiness-check"),
    path("v1/", include(router.urls)),
]
