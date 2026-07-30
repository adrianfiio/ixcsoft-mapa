import io
import zipfile

from django.test import SimpleTestCase

from apps.network_map.kmz_import import KMZAnalyzer, kml_color_to_hex


KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <Style id="green"><LineStyle><color>ff00ff00</color><width>4</width></LineStyle></Style>
  <Folder><name>ROTA 01</name>
    <Placemark><name>CDO-01</name><Point><coordinates>-51,-24,0</coordinates></Point></Placemark>
    <Placemark><name>18-1</name><Point><coordinates>-51.01,-24.01,0</coordinates></Point></Placemark>
    <Placemark><name>RT 50m</name><Point><coordinates>-51.02,-24.02,0</coordinates></Point></Placemark>
    <Placemark><name>24 FO 1000 mts</name><styleUrl>#green</styleUrl>
      <LineString><coordinates>-51,-24,0 -51.01,-24.01,0</coordinates></LineString>
    </Placemark>
  </Folder>
</Document>
</kml>"""


class Upload(io.BytesIO):
    name = "sample.kmz"


class KMZAnalyzerTests(SimpleTestCase):
    def make_upload(self):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("doc.kml", KML)
        output.seek(0)
        return Upload(output.read())

    def test_kml_color_conversion(self):
        self.assertEqual(kml_color_to_hex("ff00ff00")["hex"], "#00ff00")

    def test_analyze_alias_numeric_reserve_and_line(self):
        result = KMZAnalyzer.from_upload(self.make_upload()).analyze("sample.kmz")
        self.assertEqual(result["summary"]["points"], 3)
        self.assertEqual(result["summary"]["lines"], 1)
        self.assertEqual(result["line_color_groups"][0]["hex"], "#00ff00")
        by_name = {item["name"]: item for item in result["points"]}
        self.assertEqual(by_name["CDO-01"]["suggested_type"], "splice_box")
        self.assertEqual(by_name["18-1"]["reason"], "numeric_name")
        self.assertEqual(by_name["RT 50m"]["suggested_type"], "technical_reserve")
        self.assertEqual(result["lines"][0]["fiber_count_hint"], 24)
