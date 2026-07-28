from rest_framework.routers import DefaultRouter

from .views import (
    IXCConfigurationViewSet,
    IXCSyncExecutionViewSet,
    IXCCustomerViewSet,
    IXCLoginViewSet,
)

router = DefaultRouter()
router.register("configurations", IXCConfigurationViewSet)
router.register("executions", IXCSyncExecutionViewSet)
router.register("customers", IXCCustomerViewSet)
router.register("logins", IXCLoginViewSet)

urlpatterns = router.urls
