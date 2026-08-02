from django.urls import path

from .api import (
    equipment_monitoring_bindings,
    equipment_monitoring_poll_now,
    equipment_monitoring_profile,
    monitored_link_detail,
    monitored_links,
    project_monitoring_snapshot,
)

app_name = "snmp_monitoring"

urlpatterns = [
    path("projects/<int:project_id>/snapshot/", project_monitoring_snapshot, name="project-snapshot"),
    path("equipment/<int:equipment_id>/", equipment_monitoring_profile, name="equipment-profile"),
    path("equipment/<int:equipment_id>/bindings/", equipment_monitoring_bindings, name="equipment-bindings"),
    path("equipment/<int:equipment_id>/poll/", equipment_monitoring_poll_now, name="equipment-poll"),
    path("links/", monitored_links, name="links"),
    path("links/<int:link_id>/", monitored_link_detail, name="link-detail"),
]
