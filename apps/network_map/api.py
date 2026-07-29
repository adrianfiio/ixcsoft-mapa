
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import NetworkElement
from .serializers import NetworkElementMapSerializer


class MapElementsAPIView(APIView):

    def get(self, request):
        elements = NetworkElement.objects.filter(
            enabled=True
        )

        serializer = NetworkElementMapSerializer(
            elements,
            many=True
        )

        return Response(serializer.data)
