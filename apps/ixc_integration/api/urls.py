from rest_framework.routers import DefaultRouter

from .views import (
    IXCConfigurationViewSet,
    IXCSyncExecutionViewSet,
    IXCCustomerViewSet,
    IXCLoginViewSet,
    IXCFiberAssignmentViewSet,
)

router = DefaultRouter()
router.register("configurations", IXCConfigurationViewSet)
router.register("executions", IXCSyncExecutionViewSet)
router.register("customers", IXCCustomerViewSet)
router.register("logins", IXCLoginViewSet)
router.register("fiber-assignments", IXCFiberAssignmentViewSet)

urlpatterns = router.urls
