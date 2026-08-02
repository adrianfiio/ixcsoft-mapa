from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from apps.core.enums import OperationalStatus
from apps.snmp_monitoring.link_status import raw_link_status, transition_ready


class LinkStatusTests(SimpleTestCase):
    def test_both_ports_up_is_normal(self):
        self.assertEqual(raw_link_status(["up", "up"]), OperationalStatus.NORMAL)

    def test_one_down_is_offline(self):
        self.assertEqual(raw_link_status(["up", "down"]), OperationalStatus.OFFLINE)

    def test_missing_second_endpoint_is_no_data(self):
        self.assertEqual(raw_link_status(["up"], require_both=True), OperationalStatus.NO_DATA)

    def test_outage_debounce(self):
        now = timezone.now()
        self.assertFalse(transition_ready(
            current=OperationalStatus.NORMAL,
            candidate=OperationalStatus.OFFLINE,
            candidate_since=now - timedelta(seconds=20),
            now=now,
            outage_seconds=30,
            recovery_seconds=30,
        ))
        self.assertTrue(transition_ready(
            current=OperationalStatus.NORMAL,
            candidate=OperationalStatus.OFFLINE,
            candidate_since=now - timedelta(seconds=31),
            now=now,
            outage_seconds=30,
            recovery_seconds=30,
        ))
